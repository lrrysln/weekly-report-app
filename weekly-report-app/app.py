import pandas as pd

df = pd.DataFrame({
    'Site': ['A', 'A', 'A', 'B', 'B'],
    'Week': ['Week 1', 'Week 2', 'Week 3', 'Week 1', 'Week 2'],
    'Store Opening': pd.to_datetime([
        '2025-09-01', '2025-09-08', '2025-09-05',  # Site A: baseline, pushed, pulled in
        '2025-10-01', '2025-10-01'                # Site B: baseline, held
    ]),
    'Baseline': ['True', '', '', 'True', '']
})


trend_map = {}

for site, grp in df.groupby('Site'):
    grp = grp.sort_values('Week')  # or by a real date field if available
    for idx in grp.index:
        cur = grp.loc[idx, 'Store Opening']
        is_base = str(grp.loc[idx, 'Baseline']).strip().lower() == 'true'

        prev_idx = grp.index[grp.index.get_loc(idx) - 1] if grp.index.get_loc(idx) > 0 else None

        if is_base:
            trend_map[idx] = "⚪ Baseline"
        elif prev_idx is not None:
            prev_date = grp.loc[prev_idx, 'Store Opening']
            if pd.isna(cur):
                trend_map[idx] = "🟡 Held"
            elif cur < prev_date:
                trend_map[idx] = "🟢 Pulled In"
            elif cur > prev_date:
                trend_map[idx] = "🔴 Pushed"
            else:
                trend_map[idx] = "🟡 Held"
        else:
            trend_map[idx] = "⚪ Baseline"

df['Trend'] = df.index.map(trend_map)
