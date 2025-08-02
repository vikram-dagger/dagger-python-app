import os
import random
from typing import Annotated
from datetime import datetime

from dagger import Container, dag, Directory, DefaultPath, Doc, File, Secret, function, object_type, ReturnType


@object_type
class Book:

    source: Annotated[Directory, DefaultPath(".")]

    @function
    def env(self) -> Container:
        """Returns a container with the Python environment and the source code mounted"""
        return (
            dag.container()
            .from_("python:3.11")
            .with_directory("/app", self.source)
            .with_workdir("/app")
            .with_mounted_cache("/root/.cache/pip", dag.cache_volume("python-pip"))
            .with_exec(["pip", "install", "-r", "requirements.txt"])
        )

    @function
    async def test(self) -> str:
        """Runs the tests in the source code and returns the output"""
        postgresdb =  (
            dag.container()
            .from_("postgres:alpine")
            .with_env_variable("POSTGRES_DB", "app_test")
            .with_env_variable("POSTGRES_PASSWORD", "secret")
            .with_exposed_port(5432)
            .as_service(args=[], use_entrypoint=True)
        )

        cmd = (
            self.env()
            .with_service_binding("db", postgresdb)
            .with_env_variable("DATABASE_URL", "postgresql://postgres:secret@db/app_test")
            .with_exec(["pytest"])
        )
        return await cmd.stdout()

    @function
    def container_echo(self, string_arg: str) -> Container:
        """Returns a container that echoes whatever string argument is provided"""
        return dag.container().from_("alpine:latest").with_exec(["echo", string_arg])

    @function
    async def grep_dir(self, directory_arg: Directory, pattern: str) -> str:
        """Returns lines that match a pattern in the files of the provided Directory"""
        return await (
            dag.container()
            .from_("alpine:latest")
            .with_mounted_directory("/mnt", directory_arg)
            .with_workdir("/mnt")
            .with_exec(["grep", "-R", pattern, "."])
            .stdout()
        )
    
    @function
    async def publish(self, 
        registry: Annotated[str, Doc("Registry address")],
        username: Annotated[str, Doc("Registry username")],
        password: Annotated[Secret, Doc("Registry password")],) -> str:
        """Builds and publishes the application container to a registry"""
        await self.test()
       
    
        image_ref = f"{registry}/{username}/{random.randrange(10**8)}"
        
        return await (
            self.env()
            .with_exposed_port(8000)
            .with_registry_auth(registry, username, password)
            .publish(image_ref)
        )   