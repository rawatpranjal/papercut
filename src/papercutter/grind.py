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


# Section extraction instructions - PhD-level, concise, technical
# Target: Researchers who want to quickly get up to speed
# Philosophy: Give hints, not commands. Trust the model's judgment.
SECTION_INSTRUCTIONS = {
    "context": """Research question and headline finding. ~80 words.
What problem? What approach? What's the punchline?""",

    "core_mechanism": """What is the key mechanism/insight? ~100 words.
Explain the core idea as if to a colleague over coffee.
- What's the main causal channel or theoretical mechanism?
- Why does X lead to Y? What's the intuition?
- What makes this paper's approach clever or novel?

Example: "The paper exploits the fact that minimum wage increases
create a natural experiment. NJ raised wages while PA didn't, so
comparing employment changes across the border identifies the causal
effect. The key insight is using within-chain variation to control
for demand shocks." """,

    "prior_work": """What gap does this fill? ~60 words of prose.
What did prior work establish? What was missing? How does this paper address it?""",

    "method": """Model and identification. ~120 words. PROSE DESCRIPTION.
- What is the model/approach? (name it, don't write equations here)
- Identification strategy: what variation? what controls?
- Key assumptions and their plausibility

Equations go in key_equations. Here: describe the approach in words.
Example: "Uses a task-based production model where output aggregates task-level production. Identifies AI impact via Hulten's theorem: aggregate TFP = cost-share-weighted sum of task improvements. Assumes 20% of tasks are AI-exposed with 27% average cost savings." """,

    "results": """Main findings with numbers. ~120 words.
Point estimates, standard errors, magnitudes, sample sizes.
What do the numbers mean? Compare to benchmarks if relevant.""",

    "golden_quote": """One memorable sentence from the paper that captures the key insight.
Copy exactly as written. Return null if none stands out.""",

    "data_description": """Dataset details. ~60 words.
Source, N, time period, key variables, sample restrictions.""",

    "contribution": """What's new? ~50 words.
Be specific and technical, not vague ("contributes to literature").""",

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

    "applications": """Practical implications. ~60 words.
Policy, industry, or research applications.""",

    "limitations": """Caveats and boundary conditions. ~80 words.
Identification concerns, external validity, data limitations, restrictive assumptions.
When should you trust/not trust these findings?""",

    "key_visual": """Explain the main result figure/table. ~50 words.
What does it show? Key numbers from it?
DO NOT mention page numbers. Match the figure/table ref from metadata.
Return null if key_figure_ref was not identified.""",

    # Condensed fields for appendix table view
    "condensed_rq": """Research question in 1 sentence. What problem does this solve?
Example: "Do minimum wage increases reduce employment?" """,

    "condensed_method": """Method + data in 2 sentences max. How do they identify the effect?
Example: "DiD comparing NJ vs PA fast-food restaurants before/after NJ minimum wage increase. N=410 stores." """,

    "condensed_result": """Key result with numbers in 1 sentence.
Example: "Employment increased by 2.76 FTE (13%) in NJ vs PA, SE=1.19." """,

    "condensed_contribution": """Main contribution in 1 sentence.
Example: "First natural experiment evidence on minimum wage using establishment-level data." """,
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
                "condensed_rq", "condensed_method", "condensed_result", "condensed_contribution"
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
            if sections.get("condensed_rq"):
                result["condensed_rq"] = sections["condensed_rq"]
            if sections.get("condensed_method"):
                result["condensed_method"] = sections["condensed_method"]
            if sections.get("condensed_result"):
                result["condensed_result"] = sections["condensed_result"]
            if sections.get("condensed_contribution"):
                result["condensed_contribution"] = sections["condensed_contribution"]

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

    # Save results with executive summary
    output_path = project_dir / "extractions.json"
    output = {
        "executive_summary": executive_summary,
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
    console.print(f"[dim]Results saved to:[/dim] {output_path}")
