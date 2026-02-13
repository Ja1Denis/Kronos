
import matplotlib.pyplot as plt
import numpy as np

# Data
labels = ['Točnost (Recall@5)', 'Ušteda Tokena (Efikasnost)']
without_kronos = [15, 10]    # 15% accuracy, 10% efficiency (high usage)
with_kronos = [70.5, 90]     # 70.5% accuracy, 90% efficiency (low usage - 90% savings)

x = np.arange(len(labels))  # label locations
width = 0.35  # width of the bars

fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
ax.set_facecolor('#0d1117')

rects1 = ax.bar(x - width/2, without_kronos, width, label='Bez Kronosa (IDE Context)', color='#ff4444')
rects2 = ax.bar(x + width/2, with_kronos, width, label='S Kronosom (Surgical RAG)', color='#00d1ff')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Postotak (%)', color='white', fontsize=12)
ax.set_title('Učinak Kronosa: Inteligencija vs. Trošak', color='white', fontsize=16, pad=20)
ax.set_xticks(x)
ax.set_xticklabels(labels, color='white', fontsize=12)
ax.legend(facecolor='#0d1117', edgecolor='white', labelcolor='white')

ax.spines['bottom'].set_color('white')
ax.spines['left'].set_color('white')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')

ax.bar_label(rects1, padding=3, color='white')
ax.bar_label(rects2, padding=3, color='white')

fig.tight_layout()

plt.savefig('eval/kronos_comparison_stats.png', dpi=150)
print("✅ Grafikon generiran: eval/kronos_comparison_stats.png")
