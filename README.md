# DatasetClassifier
A new spin on manual dataset curation

![image](https://github.com/user-attachments/assets/324b67ab-0f56-4406-8992-1be21d8344a0)
*The scoring interface - quickly assign quality scores to images*

## Introduction
DatasetClassifier is a customizable tool aimed at speeding up the workflow of manual dataset curation. It is written using Python with Qt for the frontend, providing a native experience no matter what Operating System you use.

### Motivations
I'll admit, I might be a bit crazy. I like to create datasets of a broad concept, so what I often do is I boot up [Grabber](https://github.com/Bionus/imgbrd-grabber), type in some tags, and suddenly I am left with a dataset of tens of thousands of images. Obviously, not all these images are worth keeping, so manual review is needed. The first time around, I painstakingly drag/dropped images in Windows File Explorer into different folders to sort them. Never again, I said to myself, then a few weeks later I was back at it again, with an even larger dataset...

I think you see where I'm going with this. Dragging/Dropping images in Windows File Explorer is not very fun.

Surprisingly, there were no good options for manual dataset review that met my criteria, so that's where the idea came from.

### Recommended Workflow
This application is not meant to be a replacement for existing tagging/captioning tools, but rather something you can add to your pipeline to improve both your efficiency and the quality of your final dataset. DatasetClassifier is designed to be the first step in the captioning process, generally right after grabbing or deduping images. Here is how I would recommend structuring your workflow:

1. Dataset retrieval via [Grabber](https://github.com/Bionus/imgbrd-grabber)
2. Deduplication using [DupeGuru](https://github.com/arsenetar/dupeguru/)
3. **Structured dataset filtration and captioning using DatasetClassifier**
4. More refined tagging using CLIP interrogation (DeepDanbooru, etc.) or LLM-driven captions (if needed)

## How It Works
DatasetClassifier has two main phases: **Scoring** and **Tagging**. When creating a new project, you start by scoring images, and when that's done (or when you've scored enough to start working with), you move on to tagging. You can only tag images that have already been scored.

### Scoring
The scoring process is relatively straight-forward. You see an image, you determine how good that image is for your dataset, and you apply the corresponding score.

Scores use a 1-5 scale. What each number means is up to you—the numbers themselves don't affect anything except how your images get filtered during export. You can configure how these scores are displayed in the settings to match whatever system you're used to. For example, you could use a booru-styled format (masterpiece, high quality, low quality, etc.), or a PonyV6 specification (score_9_up, score_8_up, etc.). There's also a special `discard` option which removes the image from export and hides it from the tagging page.

In my own testing, I can get through about 2-3k images per hour using this approach (without any categorization).

#### Categories
While scoring, you can also apply **categories** to images. Categories are metadata flags you define yourself—they're used for organizing your export, not for captioning. Think of them as workflow labels.

Here's an example: let's say you define two categories based on how much manual work images need: `needs_editing` and `needs_cropping`. As you score, you can flag images with the relevant categories. Later when you export, you can set up rules that put images with `needs_editing` into one subfolder, `needs_cropping` into another, and images with both into a third subfolder. This makes it easy to batch your post-processing work.

### Tagging
After scoring some or all images, you move on to tagging. This is where you apply the actual captions that will end up in your training data.

The tagging process has a bit of a learning curve. Instead of free-form tagging, it uses **TagGroups**—collections of related tags that you step through in order. The idea is to enforce consistency: by working through a checklist for every image, you won't accidentally forget to tag certain aspects.

Here's an example of how you might configure your TagGroups:

```
Subject Count:
- 1girl
- 2girls
- 3girls

Background:
- simple background
- classroom
- scenery

Composition:
- portrait
- group photo
- overview
```

In this example, you would first select one or more tags from the "Subject Count" group, then move on to "Background" and select the relevant tag, then "Composition", and so on. This process repeats for every image.

Each group is customizable. If you want the "Composition" group to be optional, you can do that. If you want to enforce at least two tags for the "Background" group, you can do that too.

### Export
When you're done, DatasetClassifier exports your images along with a `.txt` (or `.caption`) file for each one containing that image's tags. This structure is compatible with most dataset tools out there, so if you need to make changes later, you can import it into your software of choice.

Images are filtered by score during export—you choose which score levels to include. Categories are used to route images into different folders based on rules you define.

## Customization
DatasetClassifier is built around the principle of customization. Most things can be tweaked, including app behaviour, theme colors, keybinds, and more.

Some of the more advanced customizations are explained below.

### TagGroup Settings
TagGroups are created on a per-project basis. Each group can contain practically unlimited tags.

Here's what each property does:

- **Required:** Whether the TagGroup must be completed before you can proceed to the next image
- **Allow Multiple:** Whether multiple tags can be selected from the group
- **Minimum Tags:** Minimum number of tags required to proceed
- **Prevent Auto Scroll:** Whether to disable automatic scrolling to the next TagGroup when the current one's conditions are met

### Rule-Based Export
With rule-based export, you can define your own rules for organizing output.

![image](https://github.com/user-attachments/assets/d76458ce-8542-4215-882a-e596b9d2a2c1)
*The export configuration window*

Exports work with priorities. The system starts with the highest priority rule and works its way down. Any images that don't match a rule get exported to the base directory.

#### Rule Ordering
Say you have these categories: `needs editing`, `needs cropping`, `complete`

You might want to export images that need a lot of manual work to their own folder, while still routing other files to their respective output paths. You can do this by creating rules with multiple categories.

The catch is that the first valid rule an image matches is the one it uses. So if you have a rule for `edit` above a rule for `edit, crop`, the second rule will never be reached. When ordering, you generally want to keep simple rules near the bottom and rules with more complex combinations near the top:

```yaml
- Category Combinations
- Single Categories
- Fallback Rule (always present)
```

In short, more specific rules need higher priority. If you have a rule requiring three categories, it should almost always be above a rule requiring two or less.

Here's a concrete example:

```yaml
3.    ['needs editing', 'needs cropping']    './edit_crop'
2.    ['needs editing']                      './edit'
1.    ['needs cropping']                     './crop'
0.    []                                     '.'
```

In this setup, images with both categories go to `./edit_crop`, images with only one go to their respective folders, and everything else (including images with the `complete` category or no categories) goes to the root export directory.

### Conditions
There are two types of conditions in DatasetClassifier that can help speed up your workflow.

#### Activation Conditions
These are rules you can apply to a TagGroup to control when it appears. You can create custom conditions like "only show this group if group X is completed, group Y has more than 3 tags, and group Z has the `from_above` tag".

When working with large datasets and lots of TagGroups, spending some time on strong activation conditions can potentially save you hours of work—you won't have to skip through irrelevant groups manually.

#### Export Conditions
Export conditions let you automatically modify tags or sort images during export based on conditions.
They use the same syntax as Activation Conditions, and are executed in order.

There are four operation types:

**Add Tags** — Adds tags to the caption, either at the start or end. Adding at the start is useful for
trigger words that need to appear first in the caption (e.g. for LoRA training). Adding at the end is
useful for tags you realized you needed halfway through tagging. For example, if you have a `Perspectives`
group with the tags `from_above`, `from_below`, `from_side`, you could create a rule that says "if the
perspectives group has more than one tag, add the `mixed perspectives` tag".

**Remove Tags** — Removes tags from the caption by exact match. Useful for stripping out tags that
shouldn't appear in certain contexts, such as removing a quality tag from images that matched a
specific condition.

**Replace Tags (Regex)** — Performs a regex search and replace across all tags in the caption.
Useful for normalizing inconsistent tags (e.g. replacing `transparent body` and `see-through body`
with a single canonical tag), or cleaning up tags before export.

**Sort into Subdirectory** — Moves images into subfolders based on conditions. Similar to how
Categories work (though categories still take precedence), but instead of being limited to one
layer of nesting, these conditions are applied relative to where the image already is. Since
conditions are executed in order, you can chain them: first sort all images with a completed
`Background` group into a `background` subfolder, then create three rules after that to further
sort them into `forest`, `city` and `beach`. The final export would look something like:

```
- background (3 folders, 0 images):
  - forest (13 images)
  - city (21 images)
  - beach (42 images)
```

This is especially useful for balancing subsets during training. By sorting images into subfolders
by concept, you can assign different repeat counts to underrepresented concepts in your training
config, ensuring the model learns each concept equally well.

#### Syntax Examples

Group completed:
```
GroupName[completed]
```

Has tag:
```
GroupName[has:tag_1]
```
or
```
GroupName2[has_all:tag_2, tag_3]
```

Advanced example:
```
(Perspectives[has:from_above] AND NOT Style[completed]) OR Style[count >= 2]
```

## Plans
- [x] **Conditional TagGroups:** TagGroups that only appear if certain conditions are met
- [x] **Conditional Tags:** Tags that automatically get added on export based on conditions
- [x] **Export Window Rework:** The export window needed a full rewrite (done!)
- [ ] **Project Export/Import:** A feature to import/export a project with all its TagGroups, images, and tag data

## Installation

### Windows
1. Install Python (version 3.8 or greater)
2. Clone the repository with `git clone https://github.com/Cruxial0/DatasetClassifier.git`
3. Run `run-win.bat`

### Mac & Linux
1. Install Python (version 3.8 or greater)
2. Clone the repository with `git clone https://github.com/Cruxial0/DatasetClassifier.git`
3. Open a terminal in the cloned folder
4. Run: `sh run-unix.sh`

## Contributing
Contributions are welcome and encouraged!
