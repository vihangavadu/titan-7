# LUCID EMPIRE :: HUMANIZATION ENGINE
# Mouse and scroll humanization algorithms

import random
import math

class HumanizationEngine:
    """Generates human-like interaction patterns."""
    
    @staticmethod
    def generate_mouse_path(start_x, start_y, end_x, end_y, num_points=20):
        """Generate realistic curved mouse path using Bézier curves."""
        control_x = (start_x + end_x) / 2 + random.randint(-50, 50)
        control_y = (start_y + end_y) / 2 + random.randint(-50, 50)
        
        points = []
        for t in [i / num_points for i in range(num_points + 1)]:
            # Quadratic Bézier curve
            x = (1-t)**2 * start_x + 2*(1-t)*t * control_x + t**2 * end_x
            y = (1-t)**2 * start_y + 2*(1-t)*t * control_y + t**2 * end_y
            points.append((int(x), int(y)))
        
        return points
    
    @staticmethod
    def generate_scroll_pattern(max_scroll=5000, natural=True):
        """Generate realistic scroll pattern."""
        if natural:
            # Human scrolling: variable speeds with pauses
            scrolls = []
            current = 0
            while current < max_scroll:
                amount = random.choice(range(100, 500, 50))
                scrolls.append(amount)
                current += amount
            return scrolls
        else:
            return [max_scroll]
    
    @staticmethod
    def get_keystroke_delay(wpm=40):
        """Get realistic keystroke delay based on words-per-minute."""
        # Average keystroke time in milliseconds
        base_delay = (60000 / wpm) / 5  # 5 chars per word
        # Add human variability (Gaussian distribution)
        return max(0.01, random.gauss(base_delay, base_delay * 0.3))
