import random
import dagger
from dagger import dag, function, object_type


@object_type
class Book:

    @function
    def env(self, source: dagger.Directory) -> dagger.Container:
        """Returns a base image"""
        return (
            dag.container()
            .from_("python:3.11")
            .with_exec(["sh", "-c", "apt-get update && apt-get install -y libpq-dev"])
            .with_directory("/app", source)
            .with_workdir("/app")
            .with_mounted_cache("/root/.cache/pip", dag.cache_volume("python-pip"))
            .with_exec(["pip", "install", "-r", "requirements.txt"])
            .with_exposed_port(8000)
            .with_entrypoint(["fastapi", "run", "main.py", "--port", "8000"])
        )

    @function
    async def test(self, source: dagger.Directory) -> str:
        """Runs tests"""
        postgres = (
            dag.container()
            .from_("postgres:15-alpine")
            .with_env_variable("POSTGRES_USER", "app_user")
            .with_env_variable("POSTGRES_PASSWORD", "secret")
            .with_file("/docker-entrypoint-initdb.d/init-dbs.sh", source.file("./init-dbs.sh"))
            .with_exposed_port(5432)
            .as_service(args=[], use_entrypoint=True)
        )

        return await (
            self.env(source)
            .with_service_binding("db", postgres)
            .with_env_variable("DATABASE_URL", "postgresql://app_user:secret@db/app_db")
            .with_env_variable("TEST_DATABASE_URL", "postgresql://app_user:secret@db/app_db_test")
            .with_exec(["pytest"])
            .stdout()
        )

    @function
    async def publish(self, source: dagger.Directory) -> str:
        """Publishes the image"""
        await self.test(source)
        return await (
            self.env(source)
            .publish(f"ttl.sh/my-fastapi-app-{random.randrange(10000)}")
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
