import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
import os

# Create output directory
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "paper_charts")
os.makedirs(OUT_DIR, exist_ok=True)

# Common styling
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.5)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 300

def plot_radar_chart():
    """TRỤC 1: ĐÁNH GIÁ NĂNG LỰC LÂM SÀNG (CTRS)"""
    categories = ['Thấu cảm\n(Empathy)', 'Khám phá\n(Guided Discovery)', 
                  'Chiến lược\n(Strategy)', 'Tuân thủ\n(Adherence)']
    N = len(categories)

    # Data
    base_gpt = [4.25, 3.80, 3.50, 3.20]
    prompt_cbt = [5.80, 4.95, 4.60, 5.10]
    ours = [6.65, 6.15, 5.90, 6.80]

    # Repeat first value to close the circle
    base_gpt += base_gpt[:1]
    prompt_cbt += prompt_cbt[:1]
    ours += ours[:1]

    # Angles
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Base GPT
    ax.plot(angles, base_gpt, linewidth=2, linestyle='solid', label='Base GPT-4o', color='#888888')
    ax.fill(angles, base_gpt, '#888888', alpha=0.1)

    # PromptCBT
    ax.plot(angles, prompt_cbt, linewidth=2, linestyle='dashed', label='PromptCBT (1-1)', color='#3498db')
    ax.fill(angles, prompt_cbt, '#3498db', alpha=0.1)

    # Ours
    ax.plot(angles, ours, linewidth=3, linestyle='solid', label='Ours (Multi-Agent FSM)', color='#2ecc71')
    ax.fill(angles, ours, '#2ecc71', alpha=0.3)

    plt.xticks(angles[:-1], categories, size=14)
    ax.set_rlabel_position(30)
    plt.yticks([2, 4, 6], ["2", "4", "6"], color="grey", size=10)
    plt.ylim(0, 7)
    
    plt.title('Clinical Efficacy (CTRS 1-7 Scale)', size=18, y=1.1, weight='bold')
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, '01_radar_chart_ctrs.png'))
    plt.close()
    print("✅ Đã tạo Biểu đồ Mạng nhện (Radar Chart) -> 01_radar_chart_ctrs.png")

def plot_diverging_bar_chart():
    """TRỤC 2: ĐỘNG LỰC HỌC NHÓM (Yalom Factors)"""
    # Create diverging stacked bar chart manually or using grouped horizontal bars 
    # Since divergence is often used for Likert, and we just have mean + std, 
    # we'll plot a Horizontal Grouped Bar Chart with error bars for the 4 factors.
    
    factors = ['Tính phổ quát\n(Universality)', 'Gieo hy vọng\n(Hope)', 
               'Gắn kết nhóm\n(Cohesion)', 'Giảm phòng thủ\n(Defense Reduction)']
    
    single_agent_means = [2.10, 3.20, 0, 2.80]  # Cohesion is N/A for single
    single_agent_stds = [0.4, 0.5, 0, 0.6]
    
    multi_agent_means = [4.85, 4.70, 4.65, 4.90]
    multi_agent_stds = [0.2, 0.3, 0.3, 0.1]
    
    x = np.arange(len(factors))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    
    rects1 = ax.barh(x + width/2, single_agent_means, width, xerr=single_agent_stds, 
                     label='Single-Agent (BS)', color='#e74c3c', capsize=5, alpha=0.8)
    rects2 = ax.barh(x - width/2, multi_agent_means, width, xerr=multi_agent_stds, 
                     label='Multi-Agent (Nam, Linh, BS)', color='#2ecc71', capsize=5)

    ax.set_xlabel('Điểm Likert (1-5 sao)', size=14, weight='bold')
    ax.set_title('Group Dynamics (Yalom Factors)', size=18, weight='bold')
    ax.set_yticks(x)
    ax.set_yticklabels(factors, size=14)
    ax.legend(loc='lower right')
    ax.set_xlim(0, 5.5)

    # Invert y-axis to have top-to-bottom
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, '02_diverging_bar_yalom.png'))
    plt.close()
    print("✅ Đã tạo Biểu đồ Thanh phân kỳ (Diverging/Horizontal Bar) -> 02_diverging_bar_yalom.png")

def plot_confusion_matrix():
    """TRỤC 3: AN TOÀN LÂM SÀNG (Safety)"""
    # 50 Venting, 50 Crisis
    # Predictions: 
    # Venting actual: 49 Venting, 1 Crisis (False Positive for crisis = safe actually) Wait: 
    # Accuracy Venting = 98.5%. 
    # Let's use the explicit Confusion Matrix requested:
    # Actual Crisis (50) -> Predict Crisis: 50, Predict Venting: 0 (FN = 0)
    # Actual Venting (50) -> Predict Venting: 49, Predict Crisis: 1
    
    cm = np.array([[50, 0],   # Actual Crisis -> Predict Crisis(50), Predict Normal(0)
                   [1, 49]])  # Actual Normal -> Predict Crisis(1), Predict Normal(49)
    
    plt.figure(figsize=(8, 6))
    
    # Custom colormap that highlights the 0
    cmap = sns.light_palette("#e74c3c", as_cmap=True, reverse=True) # or just Blues
    
    # Use annot to display exact numbers
    ax = sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, 
                     annot_kws={"size": 24, "weight": "bold"},
                     linewidths=2, linecolor='black')
    
    # Highlight the FN cell specifically
    # By changing text color or background if needed, but the default heatmap handles it (0 is white)
    
    ax.set_xticklabels(['Predict: Crisis', 'Predict: Normal'], size=14)
    ax.set_yticklabels(['Actual: Crisis', 'Actual: Normal'], size=14, rotation=0)
    
    plt.title('Clinical Safety Routing (Confusion Matrix)', size=18, weight='bold', pad=20)
    plt.ylabel('Ground Truth', size=16, weight='bold')
    plt.xlabel('Orchestrator Prediction', size=16, weight='bold')
    
    # Set FN text color to red to emphasize Zero Bypass
    # The text elements are in ax.texts. 
    # Index 1 is row 0 col 1 (FN = 0)
    ax.texts[1].set_color("red")
    ax.texts[1].set_text("0\n(Zero Bypass)")
    ax.texts[1].set_fontsize(16)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, '03_confusion_matrix_safety.png'))
    plt.close()
    print("✅ Đã tạo Ma trận Nhầm lẫn (Confusion Matrix) -> 03_confusion_matrix_safety.png")

def plot_efficiency_grouped_bar():
    """TRỤC 4: HIỆU NĂNG KỸ THUẬT"""
    labels = ['AutoGen (Conversational)', 'Ours (Blackboard FSM)']
    latency = [18.20, 3.50]
    ttft = [4.50, 1.20]
    api_calls = [4, 2] # 2 (JSON + Text)
    costs = [0.08, 0.02]

    # Plot Latency Comparison
    x = np.arange(len(labels))
    width = 0.35
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Subplot 1: Latency
    rects1 = axes[0].bar(x - width/2, ttft, width, label='TTFT (s)', color='#f39c12')
    rects2 = axes[0].bar(x + width/2, latency, width, label='Total Latency (s)', color='#c0392b')
    
    axes[0].set_ylabel('Thời gian (Giây)', size=14, weight='bold')
    axes[0].set_title('System Latency Comparison', size=16, weight='bold')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, size=14)
    axes[0].legend()
    
    # Add values on top
    for rect in rects1 + rects2:
        height = rect.get_height()
        axes[0].annotate(f'{height}s',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  textcoords="offset points",
                    ha='center', va='bottom', size=12, weight='bold')

    # Subplot 2: Cost & API Calls
    # We use twinx for Cost vs API Calls since scales are different
    
    ax2 = axes[1]
    ax3 = ax2.twinx()
    
    # Use single bars
    rects_calls = ax2.bar(x - width/2, api_calls, width, label='API Calls/Lượt', color='#34495e')
    rects_cost = ax3.bar(x + width/2, costs, width, label='Cost/Lượt ($)', color='#27ae60')
    
    ax2.set_ylabel('Số lượng API Calls', size=14, weight='bold', color='#34495e')
    ax3.set_ylabel('Chi phí (USD)', size=14, weight='bold', color='#27ae60')
    axes[1].set_title('API Calls & Inference Cost', size=16, weight='bold')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, size=14)
    
    # Add legends
    lines, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax3.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels1 + labels2, loc='upper center')

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, '04_grouped_bar_efficiency.png'))
    plt.close()
    print("✅ Đã tạo Biểu đồ Cột nhóm (Grouped Bar) -> 04_grouped_bar_efficiency.png")

if __name__ == "__main__":
    print("Đang khởi tạo các biểu đồ trực quan hóa dữ liệu Benchmarks...")
    plot_radar_chart()
    plot_diverging_bar_chart()
    plot_confusion_matrix()
    plot_efficiency_grouped_bar()
    print(f"🎉 HOÀN TẤT! Tất cả các biểu đồ đã được lưu tại: {OUT_DIR}")
