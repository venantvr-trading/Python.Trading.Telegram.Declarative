#!/usr/bin/env python3
"""
Generate architecture diagram PNG from the current ASCII diagram in README.md
"""

# noinspection PyPackageRequirements
import matplotlib.pyplot as plt
# noinspection PyPackageRequirements
from matplotlib.patches import FancyBboxPatch


# noinspection PyPackageRequirements

def create_architecture_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    # Colors
    main_color = '#2E86AB'
    component_color = '#A23B72'
    text_color = '#F18F01'
    # background_color = '#C73E1D'

    # Main container - TelegramService
    main_box = FancyBboxPatch(
        (1, 6), 12, 3,
        boxstyle="round,pad=0.1",
        facecolor=main_color,
        edgecolor='black',
        linewidth=2,
        alpha=0.8
    )
    ax.add_patch(main_box)

    # Main title
    ax.text(7, 7.5, 'TelegramService (Orchestrator)',
            ha='center', va='center', fontsize=16, fontweight='bold', color='white')

    # Component boxes
    components = [
        {'name': 'TelegramClient', 'pos': (2, 4), 'size': (4, 1.5)},
        {'name': 'HistoryManager', 'pos': (8, 4), 'size': (4, 1.5)},
        {'name': 'MessageSender', 'pos': (2, 2), 'size': (4, 1.5)},
        {'name': 'MessageReceiver', 'pos': (8, 2), 'size': (4, 1.5)}
    ]

    for comp in components:
        box = FancyBboxPatch(
            comp['pos'], comp['size'][0], comp['size'][1],
            boxstyle="round,pad=0.05",
            facecolor=component_color,
            edgecolor='black',
            linewidth=1.5,
            alpha=0.9
        )
        ax.add_patch(box)

        # Component text
        center_x = comp['pos'][0] + comp['size'][0] / 2
        center_y = comp['pos'][1] + comp['size'][1] / 2
        ax.text(center_x, center_y, comp['name'],
                ha='center', va='center', fontsize=12, fontweight='bold', color='white')

    # Connection arrows
    # From TelegramService to components
    connections = [
        ((7, 6), (4, 5.5)),  # To TelegramClient
        ((7, 6), (10, 5.5)),  # To HistoryManager
        ((4, 4), (4, 3.5)),  # TelegramClient to MessageSender
        ((10, 4), (10, 3.5))  # HistoryManager to MessageReceiver (conceptual)
    ]

    for start, end in connections:
        ax.annotate('', xy=end, xytext=start,
                    arrowprops=dict(arrowstyle='->', lw=2, color='black', alpha=0.7))

    # Title and styling
    ax.set_title('Telegram Bot Framework Architecture', fontsize=20, fontweight='bold',
                 color=text_color, pad=20)

    # Set limits and remove axes
    ax.set_xlim(0, 14)
    ax.set_ylim(1, 10)
    ax.set_aspect('equal')
    ax.axis('off')

    # Background
    fig.patch.set_facecolor('#f8f9fa')

    # Save the figure
    plt.tight_layout()
    plt.savefig('architecture_diagram.png', dpi=300, bbox_inches='tight',
                facecolor='#f8f9fa', edgecolor='none')
    plt.close()

    print("Architecture diagram saved as 'architecture_diagram.png'")


if __name__ == "__main__":
    create_architecture_diagram()
