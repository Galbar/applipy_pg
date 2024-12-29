import importlib
import inspect
import pkgutil
from functools import total_ordering
from typing import Any, override


@total_ordering
class PgMigration:
    async def migrate(self) -> None:
        raise NotImplementedError()

    def subject(self) -> str:
        raise NotImplementedError()

    def version(self) -> str:
        raise NotImplementedError()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PgMigration):
            raise TypeError('Can only compare between Migrations')
        if other.subject() != self.subject():
            raise ValueError('Subject must be the same for both Migrations')

        return other.version() == self.version()

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, PgMigration):
            raise TypeError('Can only compare between Migrations')
        if other.subject() != self.subject():
            raise ValueError('Subject must be the same for both Migrations')

        return self.version() < other.version()


class PgClassNameMigration(PgMigration):
    """
    Utility class to create Migration classes that have their subject and
    version taken from the class name, using the format
    `<subject>_<version>`.
    ```python
        class MyTopic_20240101(ClassNameMigration):
            async def migrate(self) -> None:
                ...
    ```

    Additionally, you can optionally add a suffix in the migration class name:
    ```python
        class MyTopic_20240201_SomeDescription(ClassNameMigration):
            async def migrate(self) -> None:
                ...
    ```
    """

    def __init__(self) -> None:
        assert len(self.__class__.__name__.split('_', 2)) >= 2

    @override
    def subject(self) -> str:
        return self.__class__.__name__.split('_', 1)[0]

    @override
    def version(self) -> str:
        return self.__class__.__name__.split('_', 2)[1]


def find_migrations(module_name: str) -> list[type[PgMigration]]:
    module = importlib.import_module(module_name)
    submodule_names = [f'{module.__name__}.{mi.name}' for mi in pkgutil.iter_modules(module.__path__)]
    return [
        class_obj
        for submodule_name in submodule_names
        for class_name, class_obj in
        inspect.getmembers(
            importlib.import_module(submodule_name),
            lambda obj: (
                inspect.isclass(obj)
                and issubclass(obj, PgMigration)
                and obj.__module__ == submodule_name
            ),
        )
    ]
