import os
from pathlib import Path
import shutil
from typing import List

from src.caption_handler import CaptionHandler
from src.database.database import Database
from src.export_image import ExportImage
from src.tagging.export_tag_rule import OperationType
from src.config_handler import ConfigHandler
from src.parser import parse_condition, evaluate_condition


class Exporter:
    def __init__(self, data, database: Database, config: ConfigHandler):
        self.config = config
        self.database = database
        self.caption_handler = CaptionHandler(database, config)

        self.output_dir = data['output_directory']
        self.export_rules = data['rules']
        self.scores = data['scores']
        self.seperate_by_score = data['seperate_by_score']
        self.export_captions = data['export_captions']
        self.require_captions = data['require_captions']
        self.delete_images = data['delete_images']
        self.apply_tag_rules = data.get('apply_tag_rules', True)
        self.export_images = []
        self.failed_exports = 0

        self.project_id = data.get('project_id')
        self.tag_groups = []
        self.export_tag_rules = []

        if self.project_id and self.apply_tag_rules:
            self.tag_groups = self.database.tags.get_project_tags(self.project_id)
            self.export_tag_rules = self.database.export_rules.get_project_rules(self.project_id)

    def process_export(self, images: List[ExportImage]) -> dict[str, int]:
        self.export_images = self.process_images(images)

        found_dirs = dict()

        for img in self.export_images:
            path = str(Path(img.dest_path).parent.relative_to(self.output_dir))
            if path == '.':
                path = "./"
            elif not path.startswith('.'):
                path = f"./{path}"
            if path not in found_dirs.keys():
                found_dirs[path] = 1
            else:
                found_dirs[path] += 1

        return found_dirs

    def process_images(self, images: List[ExportImage]) -> List[ExportImage]:
        output = []
        for img in images:
            if img.score not in self.scores:
                continue

            # Apply export tag rules (add, remove, replace, sort)
            if self.apply_tag_rules and self.export_tag_rules:
                self._apply_export_tag_rules(img)

            if self.require_captions:
                has_db_tags = len(img.tag_ids) > 0
                has_prepend = len(img.prepend_tags) > 0
                has_additional = len(img.additional_tags) > 0
                if not (has_db_tags or has_prepend or has_additional):
                    continue

            matched_img = self.match_rule(img)
            output.append(matched_img)
        return output

    def _apply_export_tag_rules(self, image: ExportImage):
        """
        Apply all export tag rules to an image. Rules are applied in order
        and support four operation types: add, remove, replace, sort.
        """
        if image.additional_tags is None:
            image.additional_tags = set()

        enabled_rules = [rule for rule in self.export_tag_rules if rule.enabled]

        for rule in enabled_rules:
            try:
                parsed_condition = parse_condition(rule.condition)

                if parsed_condition is None:
                    print(f"Warning: Empty condition for rule '{rule.name}'")
                    continue

                condition_met = evaluate_condition(
                    parsed_condition,
                    image.tag_ids,
                    self.tag_groups
                )

                if not condition_met:
                    continue

                if rule.operation_type == OperationType.ADD:
                    for tag in rule.tags_to_add:
                        if rule.position == "start":
                            image.prepend_tags.append(tag)
                            print(f"Rule '{rule.name}': Prepended tag '{tag}' to image {image.id}")
                        else:
                            image.additional_tags.add(tag)
                            print(f"Rule '{rule.name}': Appended tag '{tag}' to image {image.id}")

                elif rule.operation_type == OperationType.REMOVE:
                    for tag in rule.tags_to_add:
                        image.tags_to_remove.add(tag)
                        print(f"Rule '{rule.name}': Marked tag '{tag}' for removal on image {image.id}")

                elif rule.operation_type == OperationType.REPLACE:
                    pattern = rule.search_pattern
                    replacement = rule.tags_to_add[0] if rule.tags_to_add else ""
                    if pattern:
                        image.tag_replacements.append((pattern, replacement))
                        print(
                            f"Rule '{rule.name}': Added replacement "
                            f"'{pattern}' -> '{replacement}' for image {image.id}"
                        )

                elif rule.operation_type == OperationType.SORT:
                    subdir = rule.subdirectory
                    if subdir:
                        image.sort_subdirectories.append(subdir)
                        print(
                            f"Rule '{rule.name}': Sorting image {image.id} "
                            f"into subdirectory '{subdir}'"
                        )

            except Exception as e:
                print(f"Error applying export tag rule '{rule.name}': {e}")

    def export(self):
        self.clean_output_dir()
        for img in self.export_images:
            dest_dir = Path(img.dest_path).parent
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(img.source_path, img.dest_path)

            if self.delete_images:
                os.remove(img.source_path)

            if not self.export_captions:
                continue

            self.caption_handler.collect_image_captions(img)

        self.caption_handler.write_image_captions()

    def clean_output_dir(self):
        for filename in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    def output_dir_empty(self) -> bool:
        return len(os.listdir(self.output_dir)) == 0

    def match_rule(self, image: ExportImage) -> ExportImage:
        for rule in sorted(self.export_rules, key=lambda x: x.priority, reverse=True):
            if not rule.match(set(image.categories)):
                continue
            return image.apply_rule(rule, self.output_dir, self.seperate_by_score, self.config)

        print(f"WARNING: Could not match any rules for image: {image}")
        self.failed_exports += 1
        return image