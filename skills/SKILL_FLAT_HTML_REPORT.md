# SKILL: Flat HTML Report
**Last Used:** 2026-04-13
**Times Used:** 1

## Trigger
User asks for: "build a report", "show me a dashboard", "visualise this data",
"flat HTML", "chart this", "I want to see X", "make a report from this BQ link",
"share this as a report", PowerBI link given, BQ link given.

## Context — Read First
- Understand what data/metrics the user wants to see.
- Check if data is in CSV, JSON, BQ, or already in `output/`.
- Check existing dashboards in `served_dashboard/` or `output/` to match style.

## Steps

1. **Gather data** — CSV read, BQ query, or extract from existing output files.

2. **Plan sections:**
   - Executive insights (top)
   - Daily / monthly / quarterly breakdowns (middle)
   - Raw table or detail view (bottom)
   - Executive summary / takeaways (bottom)

3. **Create HTML file** — single self-contained `.html` file.
   - Tailwind CDN: `https://cdn.tailwindcss.com`
   - Chart.js CDN for charts.
   - Walmart colors (see template below).
   - WCAG 2.2 Level AA contrast.

4. **Chart.js canvas rule:**
   ```html
   <!-- ALWAYS wrap canvas in fixed-height div. responsive:true ignores canvas height attr. -->
   <div style="height:300px;position:relative;">
     <canvas id="myChart"></canvas>
   </div>
   ```

5. **Inline the data** as a JS const if small (<500 rows). Fetch JSON if large.

6. **Open in browser** after creation:
   - Windows: `start orchestration_map.html`
   - Mac: `open report.html`

7. **Share** via `share-puppy` subagent if user wants a link.

## Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Report Title</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --blue-100:#0053e2; --spark-100:#ffc220; --green-100:#2a8703;
      --red-100:#ea1100; --gray-160:#1d1d1d; --gray-10:#f2f3f4;
    }
  </style>
</head>
<body class="bg-gray-50 p-6">
  <header style="background:var(--blue-100)" class="rounded-xl px-8 py-5 mb-6">
    <h1 class="text-white text-2xl font-bold">Report Title</h1>
    <p class="text-blue-200 text-sm">Subtitle / date range</p>
  </header>

  <!-- Executive insights -->
  <div class="grid grid-cols-3 gap-4 mb-6">
    <div class="bg-white rounded-xl p-5 shadow-sm text-center">
      <div class="text-3xl font-bold" style="color:var(--blue-100)">999</div>
      <div class="text-sm text-gray-500">Metric Label</div>
    </div>
  </div>

  <!-- Chart -->
  <div class="bg-white rounded-xl p-5 shadow-sm mb-6">
    <h2 class="font-bold mb-4">Chart Title</h2>
    <div style="height:300px;position:relative;">
      <canvas id="mainChart"></canvas>
    </div>
  </div>

  <script>
    const ctx = document.getElementById('mainChart').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Label', data: [], backgroundColor: '#0053e2' }] },
      options: { responsive: true, maintainAspectRatio: false }
    });
  </script>
</body>
</html>
```

## Notes / Gotchas
- Chart.js `responsive:true` + `maintainAspectRatio:false` REQUIRES the parent div to have a fixed height. Canvas height attribute alone does nothing.
- Always test color contrast (4.5:1 for text, 3:1 for UI elements).
- Keep it self-contained — no build steps, no node_modules.
- For Walmart sharing: use `share-puppy` subagent, get a `puppy.walmart.com` link.
