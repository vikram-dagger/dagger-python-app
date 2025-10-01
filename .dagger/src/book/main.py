import random
from typing import Annotated
from datetime import datetime

import dagger
from dagger import Container, dag, Directory, DefaultPath, Doc, File, Secret, function, object_type, ReturnType


@object_type
class Book:

    source: Annotated[dagger.Directory, DefaultPath(".")]

    @function
    def env(self) -> dagger.Container:
        """Returns a container with the Python environment and the source code mounted"""
        return (
            dag.container()
            .from_("python:3.11")
            .with_directory("/app", self.source)
            .with_workdir("/app")
            .with_mounted_cache("/root/.cache/pip", dag.cache_volume("python-pip"))
            .with_exec(["pip", "install", "-r", "requirements.txt"])
            .with_exposed_port(8000)
            .with_entrypoint(["fastapi", "run", "main.py"])
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
    async def ci(self) -> str:
        """Tests and publishes the application container to a registry"""
        await self.test()
        return await (
            self.env()
            .publish(f"ttl.sh/my-fastapi-app-{random.randrange(10**8)}")
        )
