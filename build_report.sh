#!/usr/bin/env bash
# Assemble the combined report from the Markdown parts. Run from the repository root.
# Needs pandoc; PDF output also needs a LaTeX engine (e.g. texlive-xetex).
set -euo pipefail

mkdir -p build

# Fail early with a clear message if an input is missing.
for f in abstract.md intro.md methods.md results.md discussion.md conclusion.md protocol.md deviations.md; do
  [ -f "$f" ] || { echo "missing input file: $f (run from the repository root)" >&2; exit 1; }
done

# Appendices: protocol and deviations are included verbatim, with headings pushed one level down
# so they nest under the appendix titles. Content is otherwise untouched.
{
  echo "# Appendix A: Frozen protocol"
  echo
  echo "Verbatim copy of \`protocol.md\`. SHA256 and freeze tag are recorded in \`metadata/metadata.yml\` (tag \`freeze-2026-10-03\`)."
  echo
  echo "SHA256: \`$(sha256sum protocol.md | cut -d' ' -f1)\`"
  echo
  sed 's/^#/##/' protocol.md
} > build/appendix_a.md

{
  echo "# Appendix B: Deviations from the frozen protocol"
  echo
  sed 's/^#/##/' deviations.md
} > build/appendix_b.md

# Arrays keep values with spaces (the title) as single arguments.
FILES=(abstract.md intro.md methods.md results.md discussion.md conclusion.md build/appendix_a.md build/appendix_b.md)

COMMON=(
  --toc --number-sections --resource-path=.
  --metadata "title=Shutdown-framing effect on narrated priorities in Qwen3-14B"
  --metadata "author=zalckos"
  --metadata "date=2026-10-15"
)

pandoc "${FILES[@]}" "${COMMON[@]}" --standalone --embed-resources -o build/report.html
echo "wrote build/report.html"

pandoc "${FILES[@]}" "${COMMON[@]}" -o build/report.docx
echo "wrote build/report.docx"

# PDF last: it needs LaTeX, and a failure here should not hide the other two outputs.
if pandoc "${FILES[@]}" "${COMMON[@]}" --pdf-engine=xelatex -V geometry:margin=2.5cm -V mainfont="DejaVu Serif" -V monofont="Menlo" -o build/report.pdf; then
  echo "wrote build/report.pdf"
else
  echo "PDF build failed (is texlive-xetex installed?). HTML and DOCX are in build/." >&2
fi
