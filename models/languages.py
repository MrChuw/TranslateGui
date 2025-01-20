from dataclasses import dataclass
from typing import Optional, List, Any, TypeVar, Callable, Type, cast


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


@dataclass
class LibretranslateLanguage:
    code: Optional[str] = None
    name: Optional[str] = None
    targets: Optional[List[str]] = None

    @staticmethod
    def from_dict(obj: Any) -> 'LibretranslateLanguage':
        assert isinstance(obj, dict)
        code = from_union([from_str, from_none], obj.get("code"))
        name = from_union([from_str, from_none], obj.get("name"))
        targets = from_union([lambda x: from_list(from_str, x), from_none], obj.get("targets"))
        return LibretranslateLanguage(code, name, targets)

    def to_dict(self) -> dict:
        result: dict = {}
        if self.code is not None:
            result["code"] = from_union([from_str, from_none], self.code)
        if self.name is not None:
            result["name"] = from_union([from_str, from_none], self.name)
        if self.targets is not None:
            result["targets"] = from_union([lambda x: from_list(from_str, x), from_none], self.targets)
        return result


def libretranslate_languages_from_dict(s: Any) -> List[LibretranslateLanguage]:
    return from_list(LibretranslateLanguage.from_dict, s)


def libretranslate_languages_to_dict(x: List[LibretranslateLanguage]) -> Any:
    return from_list(lambda x: to_class(LibretranslateLanguage, x), x)
