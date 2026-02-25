from dataclasses import dataclass, field
from os import path
from pathlib import Path
from typing import List, Self, Set

from src.config_handler import ConfigHandler


@dataclass
class ExportRule:
    categories: Set[str]
    destination: str
    priority: int

    def match(self, categories: Set[str]) -> bool:
        if self.categories is None:
            return True
        return self.categories.issubset(categories)


@dataclass
class ExportImage:
    id: int
    source_path: str
    dest_path: str
    score: str
    categories: List[str]
    tag_ids: List[int] = field(default_factory=list)
    additional_tags: Set[str] = field(default_factory=set)
    
    def __init__(self, id: int, source_path: str, dest_path: str, score: str, categories: List[str], tag_ids: List[int] = [], additional_tags = None):
        self.id = id
        self.source_path = source_path
        self.dest_path = dest_path
        self.score = score
        self.categories = categories
        self.tag_ids = tag_ids if tag_ids is not None else []
        
        # Ensure additional_tags is always a set
        if additional_tags is None:
            self.additional_tags = set()
        elif isinstance(additional_tags, list):
            self.additional_tags = set(additional_tags)
        else:
            self.additional_tags = additional_tags

    def apply_rule(self, rule: ExportRule, output_dir, seperate_by_score: bool, config: ConfigHandler) -> Self:
        return self.__class__(
            id=self.id,
            source_path=self.source_path,
            dest_path=self.create_path(rule, output_dir, seperate_by_score, config),
            score=self.score,
            categories=self.categories,
            tag_ids=self.tag_ids,
            additional_tags=self.additional_tags
        )
    
    def create_path(self, rule: ExportRule, output_dir, seperate_by_score: bool, config: ConfigHandler) -> str:
        filename = Path(self.source_path).name
        _, scores = config.get_scores()
        if seperate_by_score:
            return path.abspath(path.join(output_dir, scores[self.score], rule.destination, filename))
        else:
            return path.abspath(path.join(output_dir, rule.destination, filename))