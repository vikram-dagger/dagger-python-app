import dagger
from typing import Annotated
from dagger import dag, function, object_type, DefaultPath


@object_type
class Book:

    source: Annotated[dagger.Directory, DefaultPath(".")]

    @function
    def env(self) -> dagger.Container:
        """Returns a Python container with the current source directory mounted and requirements installed"""
        return (
            dag.container()
            .from_("python:3.11")
            .with_mounted_directory("/app", self.source)
            .with_workdir("/app")
            .with_mounted_cache("/root/.cache/pip", dag.cache_volume("python-pip"))
            .with_exec(["pip", "install", "-r", "requirements.txt"])
        )

    @function
    async def test(self) -> str:
        """Returns the result of running unit tests using pytest"""

        postgresdb =  (
            dag.container()
            .from_("postgres:alpine")
            .with_env_variable("POSTGRES_USER", "app_user")
            .with_env_variable("POSTGRES_DB", "app_test")
            .with_env_variable("POSTGRES_PASSWORD", "secret")
            .with_exposed_port(5432)
            .as_service(args=[], use_entrypoint=True)
        )

        return await (
            self.env()
            .with_service_binding("db", postgresdb)
            .with_env_variable("DATABASE_URL", "postgresql://app_user:secret@db/app_test")
            .with_exec(["pytest"])
            .stdout()
        )

    @function
    async def publish(self) -> str:
        """Returns the container address after publishing to ttl.sh"""
        #await self.test()
        ctr = self.env()
        return await (
            ctr
            .with_exposed_port(8000)
            .with_entrypoint(["fastapi", "run", "main.py"])
            #.with_registry_auth("docker.io", "my-username", "my-password")
            #.with_registry_auth("ghcr.io", "my-username", "my-password")
            .publish("ttl.sh/fastapi-app-1234")
        )


    @function
    def container_echo(self, string_arg: str) -> dagger.Container:
        """Returns a container that echoes whatever string argument is provided"""
        return dag.container().from_("alpine:latest").with_exec(["echo", string_arg])

    @function
    async def grep_dir(self, directory_arg: dagger.Directory, pattern: str) -> str:
        """Returns lines that match a pattern in the files of the provided Directory"""
        return await (
            dag.container()
            .from_("alpine:latest")
            .with_mounted_directory("/mnt", directory_arg)
            .with_workdir("/mnt")
            .with_exec(["grep", "-R", pattern, "."])
            .stdout()
        )
