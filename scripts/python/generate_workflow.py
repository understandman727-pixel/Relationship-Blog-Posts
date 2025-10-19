#!/usr/bin/env python3
"""Generate staged blog workflow artifacts for the Relationship Blog project."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path
from textwrap import fill
from typing import Any, Dict, Iterable, List, Tuple

# The script assumes it lives two levels down from the project root.  By resolving
# ``__file__`` and walking up two directories we arrive at the repository root.
# This is used to locate configuration, data, and context artifacts relative
# to the repository structure.
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "blog_post_workflow.json"
KEYWORD_DATA_PATH = ROOT / "data" / "keyword_clusters.json"
CONTEXT_SHARED_PATH = ROOT / "artifacts" / "context.json"


def load_config() -> Dict[str, Any]:
    """Load the workflow configuration file as JSON."""
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_keyword_clusters() -> Dict[str, Any]:
    """Load keyword cluster data used for research and scoring."""
    with KEYWORD_DATA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def ensure_directory(path: Path) -> None:
    """Ensure that the given directory exists, creating parents if necessary."""
    path.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    """Convert an arbitrary string into a URL-friendly slug."""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def clean_sentence(text: str) -> str:
    """
    Strip whitespace and ensure a sentence ends with proper punctuation.

    If the input is empty, return it unchanged.  If the last character is
    not one of ".", "!", or "?", append a period.
    """
    text = text.strip()
    if not text:
        return text
    if text[-1] not in ".!?":
        return f"{text}."
    return text


def cluster_metrics(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute derived metrics for a keyword cluster.

    The score combines total volume, average click-through rate (CTR),
    difficulty, and conversion potential weighting.  It also surfaces
    commonly used metadata like top keywords, Pinterest angles, meta hooks
    and emotional drivers to simplify downstream reporting.
    """
    keywords = cluster["keywords"]
    volumes = [kw["volume"] for kw in keywords]
    difficulties = [kw["difficulty"] for kw in keywords]
    ctrs = [kw.get("ctr_estimate", 0.12) for kw in keywords]
    total_volume = sum(volumes)
    avg_difficulty = statistics.mean(difficulties)
    avg_ctr = statistics.mean(ctrs)
    conv_weight = {"High": 3.0, "Medium": 2.0, "Low": 1.0}
    weight = conv_weight.get(cluster.get("conversion_potential", "Medium"), 2.0)
    score = (total_volume * weight) + (avg_ctr * 1000) - (avg_difficulty * 45)
    top_keywords = sorted(keywords, key=lambda kw: kw["volume"], reverse=True)[:3]
    pinterest_angles = list({kw.get("pinterest_angle", "") for kw in keywords})
    meta_hooks = list({kw.get("meta_hook", "") for kw in keywords})
    emotional_drivers = list({kw.get("emotional_driver", "") for kw in keywords})
    return {
        "id": cluster["id"],
        "label": cluster["label"],
        "core_emotion": cluster.get("core_emotion", ""),
        "conversion_potential": cluster.get("conversion_potential", "Medium"),
        "product_compatibility": cluster.get("product_compatibility", ""),
        "notes": cluster.get("notes", ""),
        "total_volume": total_volume,
        "avg_difficulty": avg_difficulty,
        "avg_ctr": avg_ctr,
        "score": score,
        "keywords": keywords,
        "top_keywords": [kw["term"] for kw in top_keywords],
        "pinterest_angles": pinterest_angles,
        "meta_hooks": meta_hooks,
        "emotional_drivers": emotional_drivers,
    }


def format_markdown_table(headers: List[str], rows: Iterable[Iterable[str]]) -> str:
    """Render a simple Markdown table from headers and row values."""
    header_row = " | ".join(headers)
    separator = " | ".join(["---"] * len(headers))
    body_rows = [" | ".join(row) for row in rows]
    return "\n".join([header_row, separator, *body_rows])


def write_text_file(path: Path, content: str) -> None:
    """Write text to a file, ensuring a trailing newline."""
    path.write_text(content.strip() + "\n", encoding="utf-8")


def summarize_cluster(cluster: Dict[str, Any]) -> str:
    """Summarize a cluster for quick reference listings."""
    return (
        f"{cluster['label']} | Emotion: {cluster['core_emotion']} | "
        f"Volume: {cluster['total_volume']:,} | Avg Difficulty: {cluster['avg_difficulty']:.1f} | "
        f"Conversion: {cluster['conversion_potential']}"
    )


def compute_keyword_density(text: str, keyword: str) -> float:
    """
    Compute the density of a keyword within a body of text.

    The result is a proportion of how many times the keyword appears compared
    to the total number of words.  Keywords may span multiple words.
    """
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    if not words:
        return 0.0
    keyword_words = re.findall(r"[A-Za-z0-9']+", keyword.lower())
    count = 0
    for i in range(len(words) - len(keyword_words) + 1):
        if words[i : i + len(keyword_words)] == keyword_words:
            count += 1
    return count / len(words)


def flesch_kincaid_grade(text: str) -> float:
    """
    Estimate the Flesch–Kincaid grade level for a piece of text.

    This uses the standard formula based on words per sentence and syllables
    per word, returning a grade level rounded to two decimal places.
    """
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"[A-Za-z0-9']+", text)
    syllables = sum(estimate_syllables(word) for word in words)
    if not sentences or not words:
        return 0.0
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    grade = (0.39 * words_per_sentence) + (11.8 * syllables_per_word) - 15.59
    return round(grade, 2)


def estimate_syllables(word: str) -> int:
    """
    Estimate the number of syllables in a word using a simple heuristic.
    """
    word = word.lower()
    vowels = "aeiouy"
    syllables = 0
    prev_char_was_vowel = False
    for char in word:
        if char in vowels:
            if not prev_char_was_vowel:
                syllables += 1
            prev_char_was_vowel = True
        else:
            prev_char_was_vowel = False
    if word.endswith("e") and syllables > 1:
        syllables -= 1
    return max(syllables, 1)


def generate_paragraph(theme: str, context: Dict[str, Any], extra: Dict[str, Any]) -> str:
    """
    Generate a formatted paragraph based on a theme, context, and extra options.

    The resulting paragraph is wrapped to 100 characters wide and weaves
    together the theme, persona details, primary keyword, core emotion,
    and a call-to-action provided via ``extra``.
    """
    persona_name = context.get("persona_name", "reader")
    product = context.get("product", "the program")
    primary_keyword = context.get("primary_keyword", "relationship strategy")
    top_keywords = context.get("winning_cluster", {}).get("top_keywords", [primary_keyword])
    core_emotion = context.get("winning_cluster", {}).get("core_emotion", "emotional connection")
    tone = extra.get("tone", "warm")  # currently unused but available for future extensions
    call_to_action = extra.get(
        "cta",
        "Bookmark the ritual, screenshot the phrasing, and revisit it whenever you feel him drift."
    )
    theme_sentence = clean_sentence(theme)
    keyword_joined = ", ".join(top_keywords[:3])
    sentences = [
        theme_sentence,
        (
            f"For the {persona_name}, {product} turns everyday anxieties into leadership moments by handing her phrases like "
            f"{keyword_joined}."
        ),
        (
            f"Each delivery keeps the primary keyword '{primary_keyword}' front and center while unlocking {core_emotion.lower()} he can instantly feel."
        ),
        call_to_action,
    ]
    paragraph = " ".join(sentences)
    return fill(paragraph, width=100)


def generate_section_summary(heading: str, paragraphs: List[str]) -> str:
    """Render a Markdown section with a heading followed by paragraphs."""
    rendered = [f"## {heading}"]
    rendered.extend(paragraphs)
    rendered.append("")
    return "\n".join(rendered)


def stage1(args: argparse.Namespace, config: Dict[str, Any], keyword_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 1 — Perform research and produce strategy artifacts.

    This stage identifies the winning keyword cluster, produces breakdowns,
    documents persona information, writes SEO titles and hooks, and audits
    competitors.  It writes multiple Markdown files and returns a context
    dictionary capturing the winning cluster and related metadata.
    """
    output_dir = Path(args.output_dir)
    ensure_directory(output_dir)

    persona_profile = config["stage1"]["persona"].copy()
    persona_profile["name"] = args.persona_name or persona_profile.get("name")

    clusters = [cluster_metrics(cluster) for cluster in keyword_data["clusters"]]
    winning_cluster = max(clusters, key=lambda c: c["score"])

    today = datetime.utcnow().strftime("%Y-%m-%d")
    headers = [
        "Cluster",
        "Core Emotion",
        "Primary Keywords",
        "Total Volume",
        "Avg Difficulty",
        "Conversion",
        "Pinterest Visual Angle",
        "Meta Caption Hook",
        "Product Fit",
    ]

    rows = []
    for cluster in clusters:
        rows.append(
            [
                cluster["label"],
                cluster["core_emotion"],
                ", ".join(cluster["top_keywords"]),
                f"{cluster['total_volume']:,}",
                f"{cluster['avg_difficulty']:.1f}",
                cluster["conversion_potential"],
                "; ".join(cluster["pinterest_angles"][:2]),
                "; ".join(cluster["meta_hooks"][:2]),
                cluster["product_compatibility"],
            ]
        )

    table_md = format_markdown_table(headers, rows)

    # Step 1: Deep Research — produce detailed keyword and emotional breakdowns
    deep_research_lines = [
        "# Stage 1 — Step 1: Deep Research",
        "Goal: Identify high-ROI keywords, audience intent, and emotional resonance to drive organic clicks and conversions.",
        f"_Generated on {today} for {args.product}_",
        "",
        "## Market-Aligned Keyword Clusters",
        table_md,
        "",
        "## Emotional & Performance Breakdown",
    ]

    for cluster in clusters:
        pinterest_angles = [angle for angle in cluster["pinterest_angles"] if angle]
        meta_hooks = [hook for hook in cluster["meta_hooks"] if hook]
        breakdown_lines = [
            f"- **Cluster:** {cluster['label']}",
            f"  - Primary keywords: {', '.join(cluster['top_keywords'])}",
            f"  - Core emotional driver: {cluster['core_emotion']}",
            f"  - Estimated volume: {cluster['total_volume']:,}",
            f"  - Average SEO difficulty: {cluster['avg_difficulty']:.1f}",
            f"  - Conversion potential: {cluster['conversion_potential']}",
            f"  - Pinterest visual angles: {', '.join(pinterest_angles[:3])}",
            f"  - Meta caption hooks: {', '.join(meta_hooks[:3])}",
            f"  - Product compatibility: {cluster['product_compatibility']}",
        ]
        deep_research_lines.extend(breakdown_lines)
        deep_research_lines.append("")

    justification = (
        f"The highest scoring cluster is **{winning_cluster['label']}** thanks to a total volume of "
        f"{winning_cluster['total_volume']:,}, a {winning_cluster['conversion_potential'].lower()} conversion projection, "
        f"and emotional drivers around {', '.join(filter(None, winning_cluster['emotional_drivers']))}. "
        f"It aligns directly with {args.product} because the offer teaches devotion phrases that feel like "
        f"{winning_cluster['core_emotion'].lower()} for the {persona_profile['name']} persona."
    )

    winning_angles = [angle for angle in winning_cluster["pinterest_angles"] if angle]
    winning_hooks = [hook for hook in winning_cluster["meta_hooks"] if hook]

    deep_research_lines.extend(
        [
            "## Winner Selection & Justification",
            fill(justification, width=100),
            "",
            "## Deliverables",
            "- Unified keyword cluster summary",
            "- Emotional intent mapping",
            "- CTR forecast",
            "- Pinterest visual angles",
            "- Meta caption hooks",
            "",
            "### Unified Keyword Cluster",
            f"- Label: {winning_cluster['label']}",
            f"- Core emotion: {winning_cluster['core_emotion']}",
            f"- Primary keywords: {', '.join(winning_cluster['top_keywords'])}",
            f"- Estimated total volume: {winning_cluster['total_volume']:,}",
            f"- Average SEO difficulty: {winning_cluster['avg_difficulty']:.1f}",
            f"- Projected CTR: {winning_cluster['avg_ctr'] * 100:.1f}%",
            "",
            "### Emotional Intent Mapping",
            f"- Emotional drivers: {', '.join(filter(None, winning_cluster['emotional_drivers'])) or 'Available upon refresh'}",
            f"- Product compatibility notes: {winning_cluster['product_compatibility'] or 'Use persona language to customize.'}",
            "",
            "### CTR Forecast",
            f"- Forecasted clicks per 1K impressions: {math.floor(winning_cluster['avg_ctr'] * 1000)}",
            f"- Conversion potential: {winning_cluster['conversion_potential']}",
            "",
            "### Pinterest Visual Angles",
            *([f"- {angle}" for angle in winning_angles] or ["- Refresh angles from trend scan"]),
            "",
            "### Meta Caption Hooks",
            *([f"- {hook}" for hook in winning_hooks] or ["- Draft new hooks tied to emotional drivers"]),
        ]
    )

    write_text_file(output_dir / "step1_deep_research.md", "\n".join(str(line) for line in deep_research_lines))

    # Step 2: Define Target Persona
    persona_lines = [
        "# Stage 1 — Step 2: Define Target Persona",
        f"## Persona: {persona_profile['name']}",
        "### Pain Points",
    ]
    persona_lines.extend(f"- {item}" for item in persona_profile["pain_points"])
    persona_lines.append("\n### Desires")
    persona_lines.extend(f"- {item}" for item in persona_profile["desires"])
    persona_lines.append("\n### Search Intent")
    persona_lines.extend(f"- {item}" for item in persona_profile["search_intent"])
    persona_lines.append("\n### Keyword Map")
    persona_lines.append(f"- Primary: {persona_profile['keyword_map']['primary']}")
    persona_lines.append("- Supporting: " + ", ".join(persona_profile["keyword_map"]["supporting"]))
    write_text_file(output_dir / "step2_target_persona.md", "\n".join(persona_lines))

    # Step 3: SEO Title & Hook
    primary_keyword = winning_cluster["top_keywords"][0]
    seo_templates = config["stage1"]["seo_templates"]
    persona_short = persona_profile["name"]
    seo_title = seo_templates["title"].format(
        primary_keyword=primary_keyword.title(),
        product=args.product,
        persona_short=persona_short,
    )
    meta_description = seo_templates["meta_description"].format(
        primary_keyword=primary_keyword,
        product=args.product,
        persona_short=persona_short,
        lookback_days=args.lookback_days,
    )
    seo_hooks = seo_templates["hooks"]

    seo_lines = [
        "# Stage 1 — Step 3: SEO Title & Hook",
        f"- **SEO Title:** {seo_title}",
        f"- **Meta Description:** {meta_description}",
        f"- **Top Performing Keywords:** {', '.join(winning_cluster['top_keywords'])}",
        "",
        "## Emotional Hooks",
    ]
    seo_lines.extend(f"- {hook}" for hook in seo_hooks)
    write_text_file(output_dir / "step3_seo_title_hook.md", "\n".join(seo_lines))

    # Step 4: Competitor Audit
    competitor_lines = ["# Stage 1 — Step 4: Competitor Audit"]
    for competitor in config["stage1"]["competitor_audit"]:
        competitor_lines.extend(
            [
                f"## {competitor['domain']}",
                "### Opportunity Keywords",
                *(f"- {kw}" for kw in competitor["opportunity_keywords"]),
                "### SERP Gap Analysis",
                fill(competitor["serp_gap"], width=100),
                "",
            ]
        )
    write_text_file(output_dir / "step4_competitor_audit.md", "\n".join(competitor_lines))

    # Collect winning cluster context with filtered hooks and angles
    cluster_context = winning_cluster.copy()
    cluster_context.update(
        {
            "meta_hooks": winning_hooks,
            "pinterest_angles": winning_angles,
            "emotional_drivers": [driver for driver in winning_cluster.get("emotional_drivers", []) if driver],
        }
    )

    context = {
        "generated_on": today,
        "product": args.product,
        "persona_name": persona_profile["name"],
        "lookback_days": args.lookback_days,
        "winning_cluster": cluster_context,
        "primary_keyword": primary_keyword,
        "seo_title": seo_title,
        "meta_description": meta_description,
        "seo_hooks": seo_hooks,
        "persona_profile": persona_profile,
        "clusters": clusters,
    }

    context_path = output_dir / "context.json"
    context_path.write_text(json.dumps(context, indent=2), encoding="utf-8")
    ensure_directory(CONTEXT_SHARED_PATH.parent)
    CONTEXT_SHARED_PATH.write_text(json.dumps(context, indent=2), encoding="utf-8")
    return context


def stage2(args: argparse.Namespace, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 2 — Blog Creation & Optimization.

    Using the context generated in Stage 1, this stage produces a detailed
    outline, drafts the body of the article, assesses SEO and readability
    metrics, and prepares assets like HTML exports and image briefs.  It
    returns an updated context including slug and SEO package information.
    """
    output_dir = Path(args.output_dir)
    ensure_directory(output_dir)

    if not args.context or not Path(args.context).exists():
        raise FileNotFoundError("Stage 2 requires a context file generated by Stage 1.")
    with Path(args.context).open("r", encoding="utf-8") as fh:
        context = json.load(fh)

    stage2_config = config["stage2"]

    # Step 1: Outline generation
    outline_lines = [
        "# Stage 2 — Step 1: Outline",
        "Goal: Write, optimize, and finalize a 2,800–3,200-word blog for SEO, AEO, and conversions.",
        "",
        "## Emotional Arc",
    ]
    outline_lines.extend(f"- {item}" for item in stage2_config["outline"]["emotional_arc"])
    outline_lines.append("\n## Section Outline")
    for idx, section in enumerate(stage2_config["outline"]["sections"], start=1):
        outline_lines.append(f"{idx}. **{section['heading']}**")
        for theme in section["themes"]:
            outline_lines.append(f"   - {theme}")
    outline_lines.append("\n## External Authority Links")
    outline_lines.extend(f"- {url}" for url in stage2_config["outline"]["external_links"])
    outline_lines.append("\n## Internal Links")
    outline_lines.extend(f"- {url}" for url in stage2_config["outline"]["internal_links"])
    outline_lines.append("\n## Affiliate Link Prompt")
    outline_lines.append(stage2_config["outline"]["affiliate_prompt"].strip())
    write_text_file(output_dir / "step1_outline.md", "\n".join(outline_lines))

    affiliate_prompt_path = output_dir / "step1_5_affiliate_link_prompt.txt"
    write_text_file(affiliate_prompt_path, stage2_config["outline"]["affiliate_prompt"])

    # Generate section summaries with paragraphs for each theme
    section_summaries: List[str] = []
    for section in stage2_config["outline"]["sections"]:
        section_paragraphs = [
            generate_paragraph(
                theme,
                context,
                {
                    "tone": "warm and authoritative",
                    "cta": "Invite him into the next moment with a confident, heart-led ask.",
                },
            )
            for theme in section["themes"]
        ]
        summary_text = fill(
            (
                f"Key action: Translate '{section['heading']}' into a scheduled deliverable that keeps the primary keyword "
                f"'{context.get('primary_keyword', 'devotion blueprint')}' in the H2 and guides readers toward {context.get('product', 'the offer')}."
            ),
            width=100,
        )
        section_paragraphs.append(summary_text)
        section_summaries.append(generate_section_summary(section["heading"], section_paragraphs))

    # Embedded FAQ content
    faq_lines = ["## Embedded FAQ"]
    for faq in stage2_config["faq"]:
        faq_lines.append(f"### {faq['question']}")
        faq_lines.append(fill(faq["answer"], width=100))
        faq_lines.append("")

    persona_name = context.get("persona_name", "reader")
    winning_cluster = context["winning_cluster"]
    concluding_paragraph = fill(
        (
            f"The {persona_name} persona now has a high-converting ritual anchored in {winning_cluster['core_emotion'].lower()} "
            f"and the phrases {', '.join(winning_cluster['top_keywords'])}. Wrap Him Around Your Finger becomes the natural next "
            f"step, guiding her from anxious spirals to grounded confidence. She documents each activation inside her content "
            f"calendar, pairs it with the tracked affiliate link, and reports performance into the analytics dashboard so the "
            f"entire team can double down on what converts. Celebrate every micro-win together."
        ),
        width=100,
    )

    # Article sections: H1 title, summaries, hooks, FAQ, final close, conclusion
    article_sections: List[str] = [f"# {context.get('seo_title', 'Devotion Blueprint')}"]
    article_sections.extend(section_summaries)
    article_sections.append("## Pinterest Visual Hook")
    article_sections.append(
        fill(
            "Translate the emotional core into a three-part pin suite: quote overlays, cinematic soft-focus photography, and a "
            "story slide that teases the Wrap Him Around Your Finger ritual.",
            width=100,
        )
    )
    article_sections.append("")
    article_sections.extend(faq_lines)
    article_sections.append("## Final Empowerment Close")
    article_sections.append(
        fill(
            "You are not chasing his love—you are directing it. Combine these devotion phrases with your own intuition, anchor "
            "the energy with Mirabelle Summers' framework, and watch his commitment become the calm, steady backdrop of your life.",
            width=100,
        )
    )
    article_sections.append(concluding_paragraph)

    # Draft body includes guidance for humanization and narrative flow
    draft_sections = [
        "# Stage 2 — Step 2: Draft Body",
        "- Apply an AI humanizer pass to each section to preserve voice while optimizing for SEO/AEO.",
        "- Keep the emotional arc from Step 1 visible while drafting to maintain narrative flow.",
        "",
    ]
    draft_sections.extend(article_sections)

    draft_text = "\n".join(draft_sections)
    article_text = "\n".join(article_sections)
    draft_path = output_dir / "step2_draft_body.md"
    write_text_file(draft_path, draft_text)

    # Compute SEO metrics and readability
    words = re.findall(r"[A-Za-z0-9']+", article_text)
    word_count = len(words)

    primary_keyword = context.get("primary_keyword", "relationship rituals")
    secondary_keywords = stage2_config["seo_package_keywords"]
    primary_density = round(compute_keyword_density(article_text, primary_keyword) * 100, 2)
    secondary_density = {
        kw: round(compute_keyword_density(article_text, kw) * 100, 2) for kw in secondary_keywords
    }
    grade_level = flesch_kincaid_grade(article_text)

    # Checklist summarizing optimization metrics
    checklist_lines = [
        "# Stage 2 — Step 3: Optimization Review",
        "| Item | Target | Result | Notes |",
        "| --- | --- | --- | --- |",
        f"| Word Count | 2800–3200 | {word_count} | {'Within range' if 2800 <= word_count <= 3200 else 'Adjust paragraphs for target range'} |",
        f"| Primary Keyword Density | 1–2% | {primary_density}% | Primary keyword: {primary_keyword} |",
    ]
    for kw, density in secondary_density.items():
        checklist_lines.append(
            f"| Secondary Keyword Density ({kw}) | 0.5–1% | {density}% | {'Within range' if 0.5 <= density <= 1.0 else 'Adjust usage'} |"
        )
    headings = [line for line in article_text.splitlines() if line.startswith("## ")]
    keyword_in_headings = sum(1 for heading in headings if primary_keyword.lower() in heading.lower())
    heading_note = (
        f"{keyword_in_headings}/{len(headings)} contain primary keyword" if headings else "Add H2s to target keywords"
    )
    checklist_lines.append(
        f"| Headers include query keywords | ≥50% | {heading_note} | Continue refining headings |"
    )
    emotional_words = ["fear", "desire", "hope", "reassurance"]
    emotional_presence = {word: (word in article_text.lower()) for word in emotional_words}
    checklist_lines.append(
        "| Emotional Triggers | fear, desire, hope, reassurance | "
        + ", ".join(f"{word}:{'yes' if present else 'no'}" for word, present in emotional_presence.items())
        + " | Embed emotional vocabulary across sections |"
    )
    checklist_lines.append(
        f"| Readability (Grade Level) | 6–8 | {grade_level} | Calculated via Flesch-Kincaid estimate |"
    )
    checklist_lines.append(
        "| Links & CTAs | Internal + External + Affiliate | Outline references anchor text and CTA placements | Verify affiliate link insertion pre-publish |"
    )
    checklist_lines.append(
        "| FAQ & Pinterest Hook | Included | Present | Align visuals with emotional driver |"
    )
    write_text_file(output_dir / "step3_optimization_review.md", "\n".join(checklist_lines))

    # Step 6.5: Final markdown and HTML exports
    slug = slugify(context["seo_title"])
    final_markdown = article_text
    final_path = output_dir / "step6_5_final_draft.md"
    write_text_file(final_path, final_markdown)

    html_lines = [
        "<article class=\"devotion-blueprint\">",
        f"  <h1 style=\"text-align:center;\">{context['seo_title']}</h1>",
    ]
    for line in article_text.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            heading = line[3:]
            html_lines.append(f"  <h2 style=\"text-align:center;\">{heading}</h2>")
        elif line.strip():
            html_lines.append(f"  <p>{line.strip()}</p>")
    html_lines.append("</article>")
    html_path = output_dir / "step7_clickbank_html.html"
    write_text_file(html_path, "\n".join(html_lines))

    # SEO package JSON
    seo_package = {
        "seo_title": context["seo_title"],
        "seo_description": context["meta_description"],
        "keywords": secondary_keywords,
        "slug": slug,
        "word_count": word_count,
        "primary_keyword_density_percent": primary_density,
        "secondary_keyword_density_percent": secondary_density,
        "grade_level_estimate": grade_level,
    }
    (output_dir / "step8_5_seo_package.json").write_text(json.dumps(seo_package, indent=2), encoding="utf-8")

    # Step 9: Image creation brief
    image_brief_lines = [
        "# Stage 2 — Step 9: Image Creation & Optimization",
        f"- Hero Alt Text: {stage2_config['image_brief']['hero_alt_text']}",
        "- Thumbnail Concepts:",
    ]
    image_brief_lines.extend(f"  - {thumb}" for thumb in stage2_config["image_brief"]["thumbnails"])
    image_brief_lines.append("- Watermark: Understanding Man")
    write_text_file(output_dir / "step9_image_creation.md", "\n".join(image_brief_lines))

    # Step 8: Review & Upload instructions
    review_upload_lines = [
        "# Stage 2 — Step 8: Review & Upload",
        "- Proofread the Step 6.5 final draft for flow, tense consistency, and CTA clarity.",
        "- Verify all internal, external, and affiliate links including the requested tracking parameters.",
        "- Upload to the CMS with the centered HTML export from Step 7.",
        "- Attach Pinterest visual hook assets and thumbnail concepts as supporting media.",
        "- Log publish date and URL for Stage 4 analytics tracking.",
    ]
    write_text_file(output_dir / "step8_review_upload.md", "\n".join(review_upload_lines))

    # Update context with Stage 2 results
    updated_context = context.copy()
    updated_context.update(
        {
            "slug": slug,
            "word_count": word_count,
            "primary_keyword_density_percent": primary_density,
            "secondary_keyword_density_percent": secondary_density,
            "grade_level": grade_level,
            "seo_package": seo_package,
        }
    )
    context_path = output_dir / "context.json"
    context_path.write_text(json.dumps(updated_context, indent=2), encoding="utf-8")
    ensure_directory(CONTEXT_SHARED_PATH.parent)
    CONTEXT_SHARED_PATH.write_text(json.dumps(updated_context, indent=2), encoding="utf-8")
    return updated_context


def stage3(args: argparse.Namespace, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 3 — Cross-Platform Distribution.

    Build a distribution plan covering multiple social platforms.  The plan
    includes strategy prompts, posting structures, schedules and tracking
    UTM parameters.  Returns the updated context with distribution info.
    """
    output_dir = Path(args.output_dir)
    ensure_directory(output_dir)

    if not args.context or not Path(args.context).exists():
        raise FileNotFoundError("Stage 3 requires a context file generated by Stage 2.")
    with Path(args.context).open("r", encoding="utf-8") as fh:
        context = json.load(fh)

    stage3_config = config["stage3"]

    distribution_lines = [
        "# Stage 3 — Cross-Platform Distribution",
        "Goal: Apply Pareto principle to focus on top-performing social channels.",
        "",
        "## Strategy Prompts",
    ]
    distribution_lines.extend(f"- {prompt}" for prompt in stage3_config["prompts"])
    distribution_lines.append("")

    seo_title = context.get("seo_title", "Devotion Blueprint")
    slug = context.get("slug", slugify(seo_title))

    for platform, details in stage3_config["platforms"].items():
        distribution_lines.append(f"## {platform.replace('_', ' ')}")
        if "post_structure" in details:
            distribution_lines.append("### Post Structure")
            distribution_lines.extend(f"- {item}" for item in details["post_structure"])
        if "posting_times" in details:
            distribution_lines.append("### Posting Times")
            distribution_lines.extend(f"- {item}" for item in details["posting_times"])
        if "posts" in details:
            distribution_lines.append(f"- Total Posts: {details['posts']}")
        if "concepts" in details:
            distribution_lines.append("### Concepts")
            distribution_lines.extend(f"- {concept}" for concept in details["concepts"])
        if "best_time" in details:
            distribution_lines.append(f"- Best Time: {details['best_time']}")
        if "topics" in details:
            distribution_lines.append("### Topics")
            distribution_lines.extend(f"- {topic}" for topic in details["topics"])
        if "schedule" in details:
            distribution_lines.append("### Schedule")
            distribution_lines.extend(f"- {item}" for item in details["schedule"])
        if "prompts" in details:
            distribution_lines.append(f"- Short-Form Prompts: {details['prompts']}")
        if "posting_schedule" in details:
            distribution_lines.append("### Posting Schedule")
            distribution_lines.extend(f"- {item}" for item in details["posting_schedule"])
        distribution_lines.append(f"- Tracking UTM: ?tid=understandingman_social_{slug}")
        distribution_lines.append("")

    write_text_file(output_dir / "stage3_cross_platform_distribution.md", "\n".join(distribution_lines))

    updated_context = context.copy()
    updated_context.setdefault("distribution", {})
    updated_context["distribution"].update(
        {
            "slug": slug,
            "platforms": stage3_config["platforms"],
            "prompts": stage3_config["prompts"],
        }
    )
    context_path = output_dir / "context.json"
    context_path.write_text(json.dumps(updated_context, indent=2), encoding="utf-8")
    ensure_directory(CONTEXT_SHARED_PATH.parent)
    CONTEXT_SHARED_PATH.write_text(json.dumps(updated_context, indent=2), encoding="utf-8")
    return updated_context


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage1_parser = subparsers.add_parser("stage1", help="Run research & strategy stage")
    stage1_parser.add_argument("--output-dir", default=str(ROOT / "artifacts" / "stage1"))
    stage1_parser.add_argument("--product", default="Wrap Him Around Your Finger")
    stage1_parser.add_argument("--persona-name", default="", help="Override persona name from config")
    stage1_parser.add_argument("--lookback-days", type=int, default=30)

    stage2_parser = subparsers.add_parser("stage2", help="Run blog creation stage")
    stage2_parser.add_argument("--output-dir", default=str(ROOT / "artifacts" / "stage2"))
    stage2_parser.add_argument("--context", default=str(ROOT / "artifacts" / "stage1" / "context.json"))

    stage3_parser = subparsers.add_parser("stage3", help="Run distribution stage")
    stage3_parser.add_argument("--output-dir", default=str(ROOT / "artifacts" / "stage3"))
    stage3_parser.add_argument("--context", default=str(ROOT / "artifacts" / "stage2" / "context.json"))

    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config()

    if args.command == "stage1":
        keyword_data = load_keyword_clusters()
        context = stage1(args, config, keyword_data)
    elif args.command == "stage2":
        context = stage2(args, config)
    else:
        context = stage3(args, config)

    print(json.dumps({"status": "ok", "stage": args.command, "context_path": str(Path(args.output_dir) / "context.json")}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
