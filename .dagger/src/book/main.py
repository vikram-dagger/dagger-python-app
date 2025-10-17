import random

import dagger
from dagger import dag, function, object_type, Directory, Container


@object_type
class Book:
    @function
    def env(self, source: dagger.Directory) -> dagger.Container:
        """Returns a container with the Python environment and the source code mounted"""
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
        """Runs the tests in the source code and returns the output"""
        db = (
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
            .with_service_binding("db", db)
            .with_env_variable("DATABASE_URL", "postgresql://app_user:secret@db/app_db")
            .with_env_variable("TEST_DATABASE_URL", "postgresql://app_user:secret@db/app_db_test")
            .with_exec(["pytest"])
            .stdout()
        )

    @function
    async def publish(self, source: dagger.Directory) -> str:
        """Builds and publishes the application container image to a registry"""
        await self.test(source)
        return await (
            self.env(source)
            .publish(f"ttl.sh/my-fastapi-app-{random.randrange(10**8)}")
        )
