"""LLM-based extraction with json_repair for robust parsing."""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.progress import track

logger = logging.getLogger(__name__)
console = Console()


def _check_litellm() -> bool:
    """Check if LiteLLM is available."""
    try:
        import litellm  # noqa: F401

        return True
    except ImportError:
        return False


def generate_schema() -> None:
    """Auto-generate columns.yaml from random paper abstracts.

    Samples 3 papers and uses LLM to suggest extraction fields.
    """
    if not _check_litellm():
        raise ImportError(
            "LiteLLM is not installed. Install with: pip install 'papercutter[llm]'"
        )

    from litellm import completion

    project_dir = Path.cwd()
    md_dir = project_dir / "markdown"

    if not md_dir.exists():
        console.print("[red]Error:[/red] No markdown directory. Run 'papercutter ingest' first.")
        return

    md_files = list(md_dir.glob("*.md"))
    if not md_files:
        console.print("[red]Error:[/red] No markdown files found. Run 'papercutter ingest' first.")
        return

    # Sample up to 3 papers
    samples = random.sample(md_files, min(3, len(md_files)))
    console.print(f"Sampling [bold]{len(samples)}[/bold] papers for schema generation...")

    # Read first 3000 chars from each (abstracts)
    abstracts = "\n\n---\n\n".join([f.read_text(encoding="utf-8")[:3000] for f in samples])

    prompt = f"""Based on these paper abstracts, suggest 5-8 data fields to extract.

Focus on quantitative data that can be compared across papers (sample sizes, effect sizes, etc).

Return ONLY valid YAML in this exact format:
columns:
  - key: sample_size
    description: "Number of observations in the study"
    type: integer
  - key: effect_size
    description: "Main treatment effect coefficient"
    type: float
  - key: methodology
    description: "Research methodology used"
    type: string

Paper abstracts:
{abstracts}"""

    console.print("Calling LLM to generate schema...")

    try:
        response = completion(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        yaml_text = response.choices[0].message.content

        # Clean markdown code blocks if present
        yaml_text = yaml_text.replace("```yaml", "").replace("```", "").strip()

        # Validate YAML
        try:
            parsed = yaml.safe_load(yaml_text)
            if "columns" not in parsed:
                raise ValueError("Missing 'columns' key in YAML")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Generated YAML may be invalid: {e}")

        # Save
        output_path = project_dir / "columns.yaml"
        output_path.write_text(yaml_text, encoding="utf-8")

        console.print(f"[green]Schema saved to:[/green] {output_path}")
        console.print("[dim]Review and edit columns.yaml before running 'papercutter grind'[/dim]")

    except Exception as e:
        # Check for authentication errors (missing/invalid API key)
        error_str = str(e).lower()
        if "auth" in error_str or "api key" in error_str or "apikey" in error_str:
            console.print("[red]Error:[/red] API key not found or invalid.")
            console.print("[dim]Set your API key with: export OPENAI_API_KEY=sk-...[/dim]")
            return
        console.print(f"[red]Error generating schema:[/red] {e}")
        raise


def _plan_extraction(completion_fn: Any, content: str) -> dict[str, Any]:
    """Step 1: Analyze paper and plan what sections to extract."""
    prompt = f"""Analyze this paper for a PhD-level literature review.

EXTRACT METADATA:
- title: The actual paper title. SKIP series headers like "NBER WORKING PAPER SERIES".
  Look for the main title, usually in large font or after the header.
- authors: "First Author et al." format
- year: Publication year or "n.d."
- paper_type: THEORY (if mainly model/proofs) | EMPIRICAL (if mainly data/regressions) | SURVEY | ML

ASSESS CONTENT:
- has_core_model: true if has formal math (theory model, estimating equation, loss function)
- model_type: "structural" | "reduced_form" | "theoretical" | "none"
- has_key_figure: true if a figure/table shows THE MAIN RESULT (not background/motivation)
- key_figure_type: "figure" | "table" | "none"
- key_figure_ref: exact reference (e.g., "Figure 3", "Table 2")
  IMPORTANT: Select the figure that shows the paper's MAIN FINDING.
  Skip introductory figures (literature trends, motivation, timelines).
  Prefer: regression results, treatment effects, model predictions, key coefficients.
- key_figure_description: what it shows (1 sentence)

DECIDE SECTIONS TO EXTRACT (include relevant ones):
- context, method, results (always)
- contribution, golden_quote, limitations (always)
- key_equations + notation (if has_core_model)
- prior_work (if builds on specific literature)
- data_description (if empirical)
- key_visual (if has_key_figure)
- applications (if policy/practice implications)

Return JSON with metadata + sections_to_extract array.

PAPER TEXT:
{content[:30000]}"""

    response = completion_fn(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return response.choices[0].message.content


# Section extraction instructions - PhD-level, explanatory, technical
# Target: Researchers who want to UNDERSTAND this paper deeply
# Philosophy: Explain ideas, don't just list them. Dense but clear.
SECTION_INSTRUCTIONS = {
    "context": """Research question, approach, and headline finding. ~120 words.
What's the economic/scientific PROBLEM this addresses? Why does it matter?
What's the paper's APPROACH to solving it? (high-level)
What's the PUNCHLINE - the surprising or important finding?
Write as connected prose, not bullet points.""",

    "core_mechanism": """Explain the key mechanism/insight. ~150 words.
This is the most important section - explain the IDEA like teaching a PhD student.
- What's the main causal channel or theoretical mechanism?
- WHY does X lead to Y? Walk through the logic step by step.
- What makes this paper's approach clever, novel, or surprising?
- If empirical: what's the identification trick?
- If theoretical: what's the key modeling insight?

Write as prose. Make the reader UNDERSTAND the idea, not just know it exists.""",

    "prior_work": """What gap does this fill? ~80 words of prose.
What did prior work establish? What question remained unanswered?
How does this paper advance beyond prior work? Be specific about the contribution.""",

    "method": """Model and identification strategy. ~150 words. PROSE DESCRIPTION.
- What is the model/approach? (name it, describe key features)
- For empirics: what variation identifies the effect? What are the controls?
- For theory: what are the key assumptions and environment?
- Discuss PLAUSIBILITY of identifying assumptions or model assumptions
- Why should we believe this identifies the causal effect / captures the mechanism?

Equations go in key_equations. Here: explain the approach conceptually.
Example: "Uses difference-in-differences comparing NJ vs PA fast food stores before/after NJ's minimum wage hike. Identification assumes parallel trends - that PA stores are a valid counterfactual for NJ stores absent treatment. Tests this by showing high-wage NJ stores (unaffected by the minimum wage) track PA stores." """,

    "results": """Main findings with numbers and interpretation. ~150 words.
Report key estimates: point estimates, standard errors, confidence intervals.
Interpret MAGNITUDES - what do these numbers mean economically?
Compare to benchmarks, prior estimates, or theoretical predictions.
Discuss robustness and heterogeneity if important.""",

    "golden_quote": """One memorable sentence from the paper that captures the key insight.
Copy exactly as written. Return null if none stands out.""",

    "data_description": """Dataset details with context. ~80 words.
Source and how data was collected. Sample size and composition.
Time period and frequency. Key variables measured.
Sample restrictions and why. Any data limitations.""",

    "contribution": """What's new and why it matters? ~80 words.
Be specific: is it a new method, new data, new theoretical result?
How does it change our understanding or what we can do?
Avoid vague phrases like "contributes to the literature." """,

    "key_equations": """Core mathematical content in LaTeX. Include BOTH if present:

THEORY (structural model, equilibrium conditions):
$V(k) = \\max_c u(c) + \\beta V(k')$ s.t. $k' = f(k) - c$

EMPIRICS (estimating equation, moment conditions):
$y_{it} = \\alpha_i + \\gamma_t + \\beta D_{it} + X'_{it}\\delta + \\varepsilon_{it}$

ML (loss function, architecture):
$\\mathcal{L} = -\\sum_i y_i \\log \\hat{y}_i + \\lambda ||\\theta||^2$

CRITICAL: Define EVERY variable. Example:
"$y_{it}$ = outcome for unit $i$ at time $t$; $D_{it}$ = treatment indicator; $\\beta$ = causal effect of interest"
Skip if no meaningful math. Don't write placeholders.""",

    "notation": """Define ALL variables from key_equations. EVERY symbol must be explained.
Format: "$Y$ = outcome; $D$ = treatment; $\\beta$ = treatment effect; $\\alpha_i$ = unit fixed effect"
Be complete - a reader should understand every symbol without looking at the paper.""",

    "applications": """Practical implications. ~80 words.
Policy implications: what should policymakers do differently?
Industry applications: how can practitioners use this?
Research applications: what new questions does this open?""",

    "limitations": """Caveats and boundary conditions. ~100 words.
Identification concerns: what could bias the estimates?
External validity: when do these findings apply and when not?
Data limitations: measurement error, sample selection, etc.
Restrictive assumptions: which assumptions are questionable?
Be specific - help the reader calibrate how much to trust these results.""",

    "key_visual": """Explain the main result figure/table. ~80 words.
What does it show? How to read it?
Key numbers from it and what they mean.
Why is this figure/table the most important one?
DO NOT mention page numbers. Match the figure/table ref from metadata.
Return null if key_figure_ref was not identified.""",

    # Condensed fields for appendix table view
    "condensed_says": """What does this paper say? 3-4 sentences.
Format: "[Key claim with context]. [Why it matters]. [What's novel - method or finding]."
Example: "Minimum wage increases don't reduce employment in low-wage industries, contradicting standard theory. Uses NJ vs PA natural experiment. First study with establishment-level data and clean identification."
Explain the idea, not just state it.""",

    "condensed_theory_data": """Theory framework + data. 2-3 sentences.
If theory: what is the model structure and key assumptions?
If empirical: data source, N, key variables, time period.
Example: "Fast-food restaurants in NJ and eastern PA. N=410 stores surveyed before/after NJ's wage hike from $4.25 to $5.05." """,

    "condensed_estimation": """Estimation approach with intuition. 2-3 sentences. Include equation if meaningful.
Not just "DiD" but explain WHY this identifies the effect.
Example: "DiD comparing employment changes in NJ vs PA. Assumes PA stores are valid counterfactual for NJ absent treatment. $\\Delta E_i = \\alpha + \\beta \\text{NJ}_i + \\varepsilon_i$"
Use LaTeX for math.""",

    "condensed_result": """Key result with numbers and interpretation. 2 sentences.
Example: "Employment increased by 2.76 FTE (13%) in NJ relative to PA, t=2.03. No evidence of adverse employment effects from minimum wage increase." """,
}


def _extract_sections(
    completion_fn: Any, content: str, sections: list[str], tables: list[dict], fields_desc: str
) -> dict[str, Any]:
    """Step 2: Extract the planned sections."""
    # Build prompt with only requested sections
    fields_to_extract = {}
    for section in sections:
        if section in SECTION_INSTRUCTIONS:
            fields_to_extract[section] = SECTION_INSTRUCTIONS[section]
            # If key_equations requested, also include notation
            if section == "key_equations":
                fields_to_extract["notation"] = SECTION_INSTRUCTIONS["notation"]

    prompt = f"""Extract sections for a PhD-level literature review. Target audience: researchers who want to quickly understand this paper.

SECTIONS TO EXTRACT:
{json.dumps(fields_to_extract, indent=2)}

GUIDELINES:
- Be concise but rigorous. Respect the word limits.
- Include specific numbers (coefficients, SEs, sample sizes).
- CRITICAL: Use LaTeX notation for ALL math. Write $\sigma$ not σ, $\Omega$ not Ω, $\beta$ not β.
- For math: include both theory AND empirics if present. Use LaTeX ($...$).
- golden_quote: one memorable sentence, copied exactly. null if none.
- key_equations: real math only. Skip placeholders. MUST use LaTeX.
- Write for someone with PhD-level training in econ/stats/ML.

QUANTITATIVE FIELDS (extract into "extracted_fields"):
{fields_desc}

TABLES FROM PAPER:
{json.dumps(tables[:3], indent=2) if tables else "None"}

Return JSON with requested sections plus extracted_fields.

PAPER TEXT:
{content[:50000]}"""

    response = completion_fn(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return response.choices[0].message.content


def _extract_ref_number(ref: str) -> int | None:
    """Extract number from a figure/table reference like 'Figure 3' or 'Table 2'."""
    import re
    match = re.search(r'\d+', ref)
    return int(match.group()) if match else None


def _synthesize_papers(completion_fn: Any, extractions: list[dict]) -> str:
    """Third API call: synthesize all papers into an executive summary."""
    # Build condensed view of all papers
    paper_summaries = []
    for p in extractions:
        paper_summaries.append({
            "title": p.get("title", "Unknown"),
            "authors": p.get("authors", "Unknown"),
            "year": p.get("year", "n.d."),
            "core_finding": p.get("results", "")[:500],
            "contribution": p.get("contribution", ""),
            "method": p.get("method", "")[:300],
        })

    prompt = f"""Write an executive summary for {len(extractions)} papers. Target: PhD researchers.

PAPERS:
{json.dumps(paper_summaries, indent=2)}

GUIDELINES (not rigid structure):
- 300-400 words total
- Start with research landscape: what questions do these address?
- Summarize each paper's key finding with specific numbers
- Note tensions or agreements between papers (if natural - don't force connections)
- End with actionable takeaway
- Use **bold** for section headers if helpful
- Reference authors by name
- Be honest if papers address distinct questions"""

    response = completion_fn(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


def _categorize_papers(completion_fn: Any, extractions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Fourth API call: categorize papers into themes for logical ordering.

    This helps organize many papers into natural groupings for the condensed
    appendix table view.

    Returns:
        tuple of (papers with category fields, list of category metadata)
    """
    if len(extractions) < 2:
        # No point categorizing 1 paper
        return extractions, []

    # Build summary for LLM
    paper_summaries = [
        {
            "paper_id": p["paper_id"],
            "title": p.get("title", ""),
            "year": p.get("year", ""),
            "paper_type": p.get("paper_type", ""),
            "contribution": p.get("contribution", "")[:200],
            "method": p.get("method", "")[:200],
        }
        for p in extractions
    ]

    prompt = f"""Categorize these {len(extractions)} papers for a literature review.

PAPERS:
{json.dumps(paper_summaries, indent=2)}

TASK:
1. Identify 2-5 natural thematic categories (e.g., "Causal Inference", "Labor Economics", "Theory")
2. Assign each paper to ONE primary category
3. Order categories logically (foundational topics first, then applications)
4. Order papers within each category (chronologically by year, oldest first)

Return JSON:
{{
  "categories": [
    {{"name": "Category Name", "description": "1-sentence description of papers in this category"}}
  ],
  "assignments": [
    {{"paper_id": "exact_paper_id", "category": "Exact Category Name", "paper_order": 1}}
  ]
}}

IMPORTANT: Use exact paper_id values from the input. Category names must match exactly between categories and assignments."""

    response = completion_fn(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    # Parse response
    import json_repair
    raw = response.choices[0].message.content
    result = json_repair.loads(raw)

    categories = result.get("categories", [])
    assignments = {a["paper_id"]: a for a in result.get("assignments", [])}

    # Add category_order to categories
    for i, cat in enumerate(categories):
        cat["category_order"] = i + 1

    # Add category fields to each paper
    for paper in extractions:
        assign = assignments.get(paper["paper_id"], {})
        paper["category"] = assign.get("category", "Uncategorized")
        paper["paper_order"] = assign.get("paper_order", 99)
        # Find category_order from category name
        cat_order = next(
            (c["category_order"] for c in categories if c["name"] == paper["category"]),
            99
        )
        paper["category_order"] = cat_order

    # Sort papers by category_order, then paper_order
    extractions.sort(key=lambda p: (p.get("category_order", 99), p.get("paper_order", 99)))

    return extractions, categories


def run_extraction() -> None:
    """Extract data fields from all ingested papers using two-step LLM approach."""
    if not _check_litellm():
        raise ImportError(
            "LiteLLM is not installed. Install with: pip install 'papercutter[llm]'"
        )

    import json_repair
    from litellm import completion

    from papercutter.project import Inventory

    project_dir = Path.cwd()

    # Load inventory
    inventory = Inventory.load(project_dir)
    ingested = inventory.get_by_status("ingested")

    if not ingested:
        console.print("[red]Error:[/red] No ingested papers found. Run 'papercutter ingest' first.")
        return

    # Load schema
    schema_path = project_dir / "columns.yaml"
    if not schema_path.exists():
        console.print("[red]Error:[/red] No columns.yaml found. Run 'papercutter configure' first.")
        return

    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    columns = schema.get("columns", [])

    if not columns:
        console.print("[red]Error:[/red] No columns defined in columns.yaml")
        return

    console.print(f"Analyzing {len(ingested)} papers (two-step extraction)...")

    # Build field descriptions for CSV extraction
    fields_desc = "\n".join([
        f"- {c['key']}: {c['description']} ({c.get('type', 'string')})"
        for c in columns
    ])

    results: list[dict[str, Any]] = []

    for paper in track(ingested, description="Grinding papers..."):
        try:
            # Load content
            md_path = paper.get_markdown_path()
            tables_path = paper.get_tables_path()

            if not md_path or not md_path.exists():
                console.print(f"[yellow]Skipping {paper.id}:[/yellow] No markdown file")
                continue

            content = md_path.read_text(encoding="utf-8")

            # Load tables if available
            tables: list[dict] = []
            if tables_path and tables_path.exists():
                tables = json.loads(tables_path.read_text(encoding="utf-8"))

            # Load figures if available
            figures: list[dict] = []
            figures_path = paper.get_figures_path()
            if figures_path and figures_path.exists():
                figures = json.loads(figures_path.read_text(encoding="utf-8"))

            # STEP 1: Plan extraction (metadata + decide what sections to extract)
            raw_plan = _plan_extraction(completion, content)
            try:
                plan = json_repair.loads(raw_plan)
            except Exception:
                plan = json.loads(raw_plan)

            # Ensure mandatory sections are always included (Morning Paper style)
            sections_to_extract = plan.get("sections_to_extract", [])
            mandatory = [
                "context", "core_mechanism", "method", "results",
                "contribution", "golden_quote", "limitations",
                # Condensed fields for appendix view
                "condensed_says", "condensed_theory_data", "condensed_estimation", "condensed_result"
            ]
            for m in mandatory:
                if m not in sections_to_extract:
                    sections_to_extract.append(m)

            # Add key_equations if paper has a core model
            if plan.get("has_core_model") and "key_equations" not in sections_to_extract:
                sections_to_extract.append("key_equations")

            # Add key_visual if paper has a key figure
            if plan.get("has_key_figure") and "key_visual" not in sections_to_extract:
                sections_to_extract.append("key_visual")

            # STEP 2: Extract the planned sections
            raw_sections = _extract_sections(
                completion, content, sections_to_extract, tables, fields_desc
            )
            try:
                sections = json_repair.loads(raw_sections)
            except Exception:
                sections = json.loads(raw_sections)

            # Use LLM-extracted title, fallback to markdown
            title = plan.get("title")
            if not title or "NBER" in title.upper() or "WORKING PAPER" in title.upper():
                # Fallback: search first 20 lines for a real title
                lines = content.split("\n")[:20]
                for line in lines:
                    line = line.strip("# ").strip()
                    if line and len(line) > 10 and "NBER" not in line.upper() and "WORKING PAPER" not in line.upper():
                        title = line
                        break
                else:
                    title = "Untitled Paper"
            if len(title) > 200:
                title = title[:200] + "..."

            # Build result combining metadata from plan + sections from extraction
            result = {
                "paper_id": paper.id,
                "title": title,
                "authors": plan.get("authors", "Unknown"),
                "year": plan.get("year", "n.d."),
                "paper_type": plan.get("paper_type", "EMPIRICAL"),
                "context": sections.get("context", ""),
                "method": sections.get("method", ""),
                "results": sections.get("results", ""),
                "data": sections.get("extracted_fields", {}),  # For CSV
            }

            # Add optional sections only if present and meaningful
            if sections.get("core_mechanism"):
                result["core_mechanism"] = sections["core_mechanism"]

            if sections.get("prior_work"):
                result["prior_work"] = sections["prior_work"]

            if sections.get("data_description"):
                result["data_description"] = sections["data_description"]

            if sections.get("contribution"):
                result["contribution"] = sections["contribution"]

            # Add condensed fields for appendix view
            if sections.get("condensed_says"):
                result["condensed_says"] = sections["condensed_says"]
            if sections.get("condensed_theory_data"):
                result["condensed_theory_data"] = sections["condensed_theory_data"]
            if sections.get("condensed_estimation"):
                result["condensed_estimation"] = sections["condensed_estimation"]
            if sections.get("condensed_result"):
                result["condensed_result"] = sections["condensed_result"]

            # Add golden quote (Morning Paper style)
            if sections.get("golden_quote"):
                result["golden_quote"] = sections["golden_quote"]

            # Add practitioner hook fields from plan
            if plan.get("core_problem"):
                result["core_problem"] = plan["core_problem"]
            if plan.get("why_care"):
                result["why_care"] = plan["why_care"]
            if plan.get("model_type") and plan.get("model_type") != "none":
                result["model_type"] = plan["model_type"]

            # Only add equations if both equation and notation are present
            if sections.get("key_equations") and sections.get("notation"):
                eq = sections["key_equations"]
                # Filter out placeholder equations
                if "not provided" not in eq.lower() and "..." not in eq:
                    result["key_equations"] = eq
                    result["notation"] = sections["notation"]

            if sections.get("applications"):
                result["applications"] = sections["applications"]

            if sections.get("limitations"):
                result["limitations"] = sections["limitations"]

            # Handle key visual ("money figure") orchestration
            if plan.get("has_key_figure") and plan.get("key_figure_ref"):
                ref = plan["key_figure_ref"]
                ref_lower = ref.lower()
                ref_num = _extract_ref_number(ref)

                result["key_figure_ref"] = ref
                result["key_figure_type"] = plan.get("key_figure_type", "unknown")
                result["key_figure_description"] = plan.get("key_figure_description", "")

                # Add the LLM explanation from second call
                if sections.get("key_visual"):
                    result["key_visual_explanation"] = sections["key_visual"]

                # Try to match to actual extracted data
                if "table" in ref_lower and ref_num and tables:
                    # Tables are 1-indexed in papers
                    if ref_num <= len(tables):
                        result["key_visual_data"] = tables[ref_num - 1]
                        result["key_visual_type"] = "table"

                elif "figure" in ref_lower and ref_num and figures:
                    # Figures are 1-indexed in papers
                    if ref_num <= len(figures):
                        fig = figures[ref_num - 1]
                        result["key_visual_path"] = fig.get("image_path", "")
                        result["key_visual_type"] = "figure"

            results.append(result)

            # Update paper status
            paper.status = "extracted"

        except Exception as e:
            # Check for authentication errors (missing/invalid API key)
            error_str = str(e).lower()
            if "auth" in error_str or "api key" in error_str or "apikey" in error_str:
                console.print("\n[red]Error:[/red] API key not found or invalid.")
                console.print("[dim]Set your API key with: export OPENAI_API_KEY=sk-...[/dim]")
                return
            console.print(f"[red]Error extracting {paper.id}:[/red] {e}")
            results.append({
                "paper_id": paper.id,
                "title": paper.filename,
                "authors": "Unknown",
                "year": "n.d.",
                "paper_type": "UNKNOWN",
                "context": f"Extraction failed: {e}",
                "method": "",
                "results": "",
                "data": {},
            })

    # STEP 3: Synthesize all papers into executive summary (third API call)
    executive_summary = None
    if len(results) >= 2:
        console.print("\nSynthesizing papers into executive summary...")
        try:
            executive_summary = _synthesize_papers(completion, results)
            console.print("[green]Executive summary generated[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not generate executive summary: {e}")

    # STEP 4: Categorize papers for logical ordering in condensed view (fourth API call)
    categories = []
    if len(results) >= 2:
        console.print("Categorizing papers...")
        try:
            results, categories = _categorize_papers(completion, results)
            console.print(f"[green]Organized into {len(categories)} categories[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not categorize papers: {e}")

    # Save results with executive summary and categories
    output_path = project_dir / "extractions.json"
    output = {
        "executive_summary": executive_summary,
        "categories": categories,
        "papers": results,
    }
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save inventory
    inventory.save(project_dir)

    # Summary
    console.print()
    console.print(f"[green]Extracted:[/green] {len(results)} papers")
    if executive_summary:
        console.print("[green]Executive summary:[/green] included")
    if categories:
        console.print(f"[green]Categories:[/green] {len(categories)}")
    console.print(f"[dim]Results saved to:[/dim] {output_path}")
