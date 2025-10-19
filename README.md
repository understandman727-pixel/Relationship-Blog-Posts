# Relationship Blog Posts

This repository serves two complementary automation flows:

- a daily-updated snapshot of the newest relationship-focused articles gathered from configured RSS and Atom feeds, and
- a staged production pipeline that researches, drafts, and distributes long-form relationship content for the "Wrap Him Around Your Finger" program.

Use the README as a hub for keeping the subscriber-facing blog roll current while also generating the internal strategy assets that feed your editorial calendar.

## Latest posts

The list below is rebuilt automatically from the configured feeds.

<!-- BLOG-POST-LIST:START -->
- [How to Get His Attention Back (Without Begging) — 7 Feminine Energy Secrets That Make Him Chase You Again](https://understandman727.blogspot.com/2025/10/how-to-get-his-attention-back-without.html)
- [How to Rebuild Emotional Safety After a Breakup](https://understandman727.blogspot.com/2025/10/how-to-rebuild-emotional-safety-after.html)
- [Say These 3 Lines & He Becomes Emotionally Closer #WhyMenPullAway #GetHi...](https://understandman727.blogspot.com/2025/10/say-these-3-lines-he-becomes.html)
- [Why Men Pull Away & How to Get Him Back — Psychology-Backed Relationship Guide](https://understandman727.blogspot.com/2025/10/why-men-pull-away-how-to-get-him-back.html)
- [Breaking Free from Anxious Attachment: Proven Treatments to Calm Relationship Anxiety & Capture His Heart with Passion Phrases](https://understandman727.blogspot.com/2025/10/breaking-free-from-anxious-attachment.html)
<!-- BLOG-POST-LIST:END -->

## Feed sync automation

1. Feed URLs live in [`config/blogs.json`](config/blogs.json). Each entry names the publication and the URL of the RSS/Atom feed to follow.
2. The Python helper at [`scripts/python/update_readme.py`](scripts/python/update_readme.py) downloads or reuses cached feed data, extracts the latest posts, and rewrites the section above.
3. A sample feed in [`data/sample_feed.xml`](data/sample_feed.xml) keeps local runs deterministic when network access is not available.

Run the updater locally with Python 3.11 or newer:

```bash
python scripts/python/update_readme.py
```

To regenerate the list without hitting the network, add the `--offline` flag to reuse the bundled sample feed.

GitHub Actions keeps the list in sync via [`.github/workflows/update-readme.yml`](.github/workflows/update-readme.yml). The workflow runs daily, can be triggered manually, and fires whenever `config/blogs.json` changes so feed updates propagate immediately.

## Staged blog workflow generator

Beyond the public feed, the repository also packages a research-to-distribution pipeline defined in [`config/blog_post_workflow.json`](config/blog_post_workflow.json) and backed by keyword intelligence in [`data/keyword_clusters.json`](data/keyword_clusters.json). The orchestration script [`scripts/python/generate_workflow.py`](scripts/python/generate_workflow.py) produces deliverables across three stages:

1. **Stage 1 – Research & Strategy** builds persona insights, keyword cluster tables, SEO hooks, and competitor audits.
2. **Stage 2 – Creation & Optimization** writes outlines, drafts modular article sections, calculates keyword densities, and exports SEO/HTML packages.
3. **Stage 3 – Cross-Platform Distribution** converts the winning angle into platform-specific posting plans and tracking parameters.

Each stage emits Markdown, JSON, and HTML artifacts to the `artifacts/` directory so writers, editors, and channel owners can collaborate from the same source of truth.

### Configuration highlights

- `stage1.persona` defines the default audience, pain points, desires, and keyword map. Override the persona name at run time with `--persona-name`.
- `stage1.seo_templates` supplies string templates for the SEO title, meta description, and emotional hooks.
- `stage2.outline` lists the emotional arc, section headings, key themes, authority links, and the affiliate-link prompt inserted into the drafts.
- `stage2.faq`, `stage2.seo_package_keywords`, and `stage2.image_brief` fine-tune downstream assets like embedded FAQs, keyword density targets, and creative directions.
- `stage3.platforms` captures distribution schedules, concepts, and CTA prompts for Instagram Reels, TikTok, Pinterest, and future channels.

### Running the stages

Execute each stage from the repository root. The later stages read the context files generated previously, so run them in order unless you provide custom paths.

```bash
# Stage 1 – Research & Strategy
python scripts/python/generate_workflow.py stage1 --output-dir artifacts/stage1

# Stage 2 – Creation & Optimization
python scripts/python/generate_workflow.py stage2 --context artifacts/stage1/context.json --output-dir artifacts/stage2

# Stage 3 – Cross-Platform Distribution
python scripts/python/generate_workflow.py stage3 --context artifacts/stage2/context.json --output-dir artifacts/stage3
```

The script prints a JSON summary pointing to the context file for each stage. You can pass alternate `--output-dir` and `--context` values to plug the pipeline into bespoke folder structures or downstream automation.

## Repository conventions

- All generated artifacts live under `artifacts/` and can be safely deleted between runs.
- Keep configuration values human-readable—keyword volumes, emotional drivers, and CTA copy should be easy to tweak without editing Python code.
- When contributing new automation, ensure scripts run with the standard library only so GitHub Actions can execute them without extra dependencies.
