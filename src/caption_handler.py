from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import os
import re
from src.export_image import ExportImage
from src.config_handler import ConfigHandler
from src.database.database import Database


@dataclass
class Caption():
    def __init__(self, tag_id: int, group_id: int, tag_name: str, tag_order: int, group_order: int):
        self.tag_id = tag_id
        self.group_id = group_id
        self.tag_name = tag_name
        self.tag_order = tag_order
        self.group_order = group_order


class CaptionHandler():
    def __init__(self, database: Database, config_handler: ConfigHandler):
        self.db = database
        self.config_handler = config_handler
        self.image_captions: dict[str, str] = {}

    def collect_image_captions(self, image: ExportImage):
        """
        Collect captions for an image from database tags, then apply
        remove, replace, and add operations from export tag rules.
        """
        caption_parts = []

        # Prepend tags go first (e.g. trigger words)
        if hasattr(image, 'prepend_tags') and image.prepend_tags:
            caption_parts.extend(image.prepend_tags)

        # Get database tags
        image_tag_ids = self.db.tags.get_image_tags(image.id)

        if len(image_tag_ids) > 0:
            captions: list[Caption] = []

            for caption in self.db.tags.get_tags_from_ids(image_tag_ids):
                captions.append(Caption(*caption))

            captions.sort(key=lambda x: (x.group_order, x.tag_order))
            caption_parts.extend([caption.tag_name for caption in captions])

        # Apply removals: drop any tag that matches a removal entry
        if image.tags_to_remove:
            caption_parts = [
                tag for tag in caption_parts
                if tag not in image.tags_to_remove
            ]

        # Apply regex replacements in order
        if image.tag_replacements:
            for pattern, replacement in image.tag_replacements:
                try:
                    compiled = re.compile(pattern)
                    new_parts = []
                    for tag in caption_parts:
                        result = compiled.sub(replacement, tag)
                        # If replacement emptied the tag, drop it
                        if result.strip():
                            new_parts.append(result)
                    caption_parts = new_parts
                except re.error as e:
                    print(f"Invalid regex pattern '{pattern}': {e}")

        # Add additional tags (from "add" rules)
        if hasattr(image, 'additional_tags') and image.additional_tags:
            if isinstance(image.additional_tags, set):
                additional = sorted(image.additional_tags)
            else:
                additional = list(image.additional_tags)
            caption_parts.extend(additional)

        if caption_parts:
            self.image_captions[image.dest_path] = ', '.join(caption_parts)

    def write_single_caption(self, image_path, caption):
        with open(image_path, 'w') as f:
            f.write(caption)

    def write_image_captions(self):
        file_extension = self.config_handler.get_value('export_options.caption_format')
        file_tasks = [
            (f'{"".join(dest_path.split(".")[0:-1])}{file_extension}', caption)
            for dest_path, caption in self.image_captions.items()
        ]

        directories = {os.path.dirname(path) for path, _ in file_tasks}
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        with ThreadPoolExecutor() as executor:
            executor.map(lambda x: self.write_single_caption(*x), file_tasks)