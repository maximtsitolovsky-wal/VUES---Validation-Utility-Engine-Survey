import json
d=json.load(open('ui/team_dashboard_data.json'))
s=d.get('scout',{})

with open('scout_stats.txt', 'w') as f:
    f.write(f"total_submissions: {s.get('total_submissions')}\n")
    f.write(f"unique_submissions: {s.get('unique_submissions')}\n")
    f.write(f"completed: {s.get('completed')}\n")
    f.write(f"excel_total: {s.get('excel_total')}\n")
    f.write(f"remaining: {s.get('remaining')}\n")
    f.write(f"records count: {len(s.get('records',[]))}\n")
    f.write(f"scout_stats_error: {s.get('scout_stats_error')}\n")
