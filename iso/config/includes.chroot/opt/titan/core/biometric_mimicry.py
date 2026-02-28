# LUCID EMPIRE :: BIOMETRIC MIMICRY MODULE
# Purpose: Defeats BehaviorSec/BioCatch using Fitts's Law, Keystroke Dynamics, and Gaussian Noise.

import asyncio
import random
import math
import time
import os
import numpy as np
from scipy.interpolate import CubicSpline
try:
    import onnxruntime as ort
except ImportError:
    ort = None

class BiometricMimicry:
    def __init__(self, page, model_path="assets/models/ghost_motor_v5.onnx"):
        self.page = page
        self.model_path = model_path
        self.session = None
        if ort and os.path.exists(self.model_path):
            try:
                self.session = ort.InferenceSession(self.model_path)
            except Exception as e:
                print(f" [!] Failed to load GAN model: {e}")

    # --- MOUSE DYNAMICS (GAN Trajectories & Fitts's Law) ---
    
    async def generate_gan_trajectory(self, start_x, start_y, end_x, end_y):
        """
        Uses the GAN model to generate a human-like trajectory (Plan 5.1).
        """
        if not self.session:
            return None
            
        # Prepare input for the model (simplified example)
        # Real model would take start/end coordinates and distance
        input_data = np.array([[start_x, start_y, end_x, end_y]], dtype=np.float32)
        input_name = self.session.get_inputs()[0].name
        
        try:
            outputs = self.session.run(None, {input_name: input_data})
            return outputs[0] # Returns array of (x, y) coordinates
        except Exception as e:
            print(f" [!] GAN inference error: {e}")
            return None

    async def human_move(self, target_x, target_y):
        """
        Moves the mouse to (target_x, target_y) using GAN trajectories or fallback.
        """
        # Get current mouse position (simulated/randomized start)
        start_x = random.randint(0, 1920)
        start_y = random.randint(0, 1080)
        
        # Try GAN trajectory first (Plan 5.1)
        trajectory = await self.generate_gan_trajectory(start_x, start_y, target_x, target_y)
        
        if trajectory is not None:
            for point in trajectory:
                await self.page.mouse.move(point[0], point[1])
                await asyncio.sleep(random.uniform(0.005, 0.012))
            return

        # Fallback to S-curve velocity profile (Plan 5.2)
        distance = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
        if distance < 1:
            return

        steps = max(15, int(distance / random.randint(10, 20)))
        
        for i in range(steps + 1):
            t = i / steps
            # Cubic easing for velocity profile
            velocity = 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2
                
            curr_x = start_x + (target_x - start_x) * velocity
            curr_y = start_y + (target_y - start_y) * velocity
            
            # Micro-tremors (Plan 5.1: 10-12Hz noise)
            tremor_x = math.sin(time.time() * 12) * random.uniform(0.1, 0.4)
            tremor_y = math.cos(time.time() * 11) * random.uniform(0.1, 0.4)
            
            await self.page.mouse.move(curr_x + tremor_x, curr_y + tremor_y)
            await asyncio.sleep(random.uniform(0.007, 0.015))

    def generate_bezier_curve(self, start_x, start_y, end_x, end_y):
        """Generate a Bezier curve with randomized control points"""
        # Control points placed randomly along the path
        ctrl_x1 = start_x + (end_x - start_x) * random.uniform(0.2, 0.4)
        ctrl_y1 = start_y + (end_y - start_y) * random.uniform(0.1, 0.3)
        ctrl_x2 = start_x + (end_x - start_x) * random.uniform(0.6, 0.8)
        ctrl_y2 = start_y + (end_y - start_y) * random.uniform(0.7, 0.9)
        
        return [
            start_x, start_y,
            ctrl_x1, ctrl_y1,
            ctrl_x2, ctrl_y2,
            end_x, end_y
        ]
        
    def add_micro_tremors(self, points):
        """Add micro-tremors to the points"""
        tremored_points = []
        for i in range(0, len(points), 2):
            x = points[i] + random.uniform(-0.5, 0.5)
            y = points[i+1] + random.uniform(-0.5, 0.5)
            tremored_points.extend([x, y])
        return tremored_points
        
    async def human_move_gan(self, start_x, start_y, end_x, end_y):
        """Simulate human-like mouse movement"""
        # Generate the base Bezier curve
        bezier_points = self.generate_bezier_curve(start_x, start_y, end_x, end_y)
        # Add micro-tremors
        points = self.add_micro_tremors(bezier_points)
        
        # Convert points to a path string
        path_str = "M{},{} C{}, {}, {}, {}, {}, {}".format(*points)
        
        # Use Playwright to move the mouse along the path
        await self.page.mouse.move(points[0], points[1])
        for i in range(2, len(points), 6):
            await self.page.mouse.move(points[i], points[i+1])
        
    async def human_click(self, selector=None, x=None, y=None):
        """
        Simulates a human click with hesitation and variable hold duration.
        """
        if selector:
            box = await self.page.locator(selector).bounding_box()
            if not box:
                return
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2

        # 1. Move to target
        await self.human_move(x, y)
        
        # 2. Target Verification Pause (Cognitive Processing)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # 3. Mouse Down
        await self.page.mouse.down()
        
        # 4. Hold Duration (Physical Mechanics)
        await asyncio.sleep(random.uniform(0.08, 0.15))
        
        # 5. Mouse Up
        await self.page.mouse.up()

    # --- KEYSTROKE DYNAMICS (Typing Rhythms & Plan 5.3) ---

    async def human_type(self, selector, text):
        """
        Types text with human-like rhythms, typos, and corrections.
        """
        element = self.page.locator(selector)
        await element.click() # Focus
        
        for char in text:
            # 1. Random typo injection (Plan 5.3: Error Correction)
            if random.random() < 0.02:
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await self.page.keyboard.type(wrong_char)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.15, 0.35))

            # 2. Key Overlap (Plan 5.3): next key down before previous key up
            # Playwright's keyboard.type doesn't easily support overlap, 
            # so we use down/up manually for critical sequences
            
            # Flight Time (latency between keys)
            delay = random.uniform(0.08, 0.22)
            
            # 3. Burst rhythm (cognitive load / Plan 5.3)
            if random.random() < 0.15:
                delay += random.uniform(0.3, 0.7) # Thinking pause
            
            await asyncio.sleep(delay)
            
            # Simulated key stroke with overlap logic
            await self.page.keyboard.down(char)
            await asyncio.sleep(random.uniform(0.05, 0.1)) # Hold time
            await self.page.keyboard.up(char)

    async def human_type_advanced(self, selector, text):
        """
        Types text with human-like rhythms, typos, and corrections.
        """
        element = self.page.locator(selector)
        await element.click() # Focus
        
        for char in text:
            # 1. Random typo injection (Plan 5.3: Error Correction)
            if random.random() < 0.02:
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await self.page.keyboard.type(wrong_char)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.15, 0.35))

            # 2. Key Overlap (Plan 5.3): next key down before previous key up
            # Playwright's keyboard.type doesn't easily support overlap, 
            # so we use down/up manually for critical sequences
            
            # Flight Time (latency between keys)
            delay = random.uniform(0.08, 0.22)
            
            # 3. Burst rhythm (cognitive load / Plan 5.3)
            if random.random() < 0.15:
                delay += random.uniform(0.3, 0.7) # Thinking pause
            
            await asyncio.sleep(delay)
            
            # Simulated key stroke with overlap logic
            await self.page.keyboard.down(char)
            await asyncio.sleep(random.uniform(0.05, 0.1)) # Hold time
            await self.page.keyboard.up(char)

    async def human_scroll(self):
        """
        Variable speed scrolling with reading pauses (Plan 5.2).
        """
        for _ in range(random.randint(3, 7)):
            scroll_amount = random.randint(200, 600)
            await self.page.mouse.wheel(0, scroll_amount)
            # Pause to "read"
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Occasional micro-scroll up
            if random.random() < 0.1:
                await self.page.mouse.wheel(0, -100)
                await asyncio.sleep(random.uniform(0.5, 1.0))
