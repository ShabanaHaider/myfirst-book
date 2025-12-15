# Capstone Project: The Autonomous Humanoid

This capstone project integrates all concepts learned throughout the course to create an autonomous humanoid robot capable of understanding voice commands, processing visual information, planning actions, and executing manipulation tasks. Students will synthesize knowledge from all modules to build a complete AI-driven humanoid system.

## Learning Objectives
By the end of this capstone project, students will be able to:
- Integrate voice recognition, computer vision, cognitive planning, and manipulation
- Design and implement a complete AI-humanoid interaction pipeline
- Debug and troubleshoot complex multi-module systems
- Evaluate the performance of integrated AI-robotic systems
- Document and present a complete technical project

## Project Overview

The Autonomous Humanoid project brings together all the components learned in previous modules into a unified system. The robot will be able to:
- Receive and understand voice commands
- Process visual information to identify objects and navigate
- Plan actions based on natural language instructions
- Execute manipulation tasks to interact with the environment

## System Architecture

The complete autonomous humanoid system consists of several interconnected components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Voice Input   │───▶│  NLP Processing  │───▶│  Task Planner   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                    ┌─────────────────┐               ▼
                    │  Perception     │◀───────────┌─────────┐
                    │   System        │           │  Action │
                    └─────────────────┘           │ Executor│
                           │                      └─────────┘
                           ▼                           │
                    ┌─────────────────┐               │
                    │  Navigation &   │◀──────────────┘
                    │ Manipulation    │
                    └─────────────────┘
```

### Component Descriptions

1. **Voice Input System**: Captures and processes spoken commands
2. **NLP Processing**: Converts speech to text and interprets meaning
3. **Task Planner**: Generates action sequences based on commands
4. **Perception System**: Processes visual and sensor data
5. **Action Executor**: Executes low-level robot actions
6. **Navigation & Manipulation**: Handles movement and object interaction

## Implementation Phases

### Phase 1: Architecture and Setup (Week 1)

#### Setup Tasks
- Create project directory structure
- Set up ROS 2 workspace with all required dependencies
- Configure simulation environment
- Initialize version control

#### Directory Structure
```
autonomous-humanoid/
├── src/
│   ├── voice_interface/
│   ├── nlp_planner/
│   ├── perception/
│   ├── action_executor/
│   └── integration/
├── config/
├── launch/
├── test/
└── docs/
```

#### Initial Configuration
```bash
# Create the workspace
mkdir -p autonomous_humanoid_ws/src
cd autonomous_humanoid_ws

# Install dependencies
sudo apt update
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup
sudo apt install ros-humble-openni2-launch ros-humble-rgbd-launch

# Create main node
cd src
git clone https://github.com/your-voice-package.git
git clone https://github.com/your-perception-package.git
```

### Phase 2: Component Integration (Week 2)

#### Voice Command Integration
Implement the voice recognition system that will receive and process natural language commands:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import speech_recognition as sr
import openai

class VoiceCommandNode(Node):
    def __init__(self):
        super().__init__('voice_command_node')
        self.publisher = self.create_publisher(String, 'natural_language_command', 10)
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)

        self.get_logger().info('Voice Command Node Started')

        # Start listening in a separate thread
        self.create_timer(0.1, self.listen_for_commands)

    def listen_for_commands(self):
        try:
            with self.microphone as source:
                self.get_logger().info('Listening for commands...')
                audio = self.recognizer.listen(source, timeout=5.0)

            # Recognize speech using Google's service
            command_text = self.recognizer.recognize_google(audio)
            self.get_logger().info(f'Heard command: {command_text}')

            # Publish the recognized command
            msg = String()
            msg.data = command_text
            self.publisher.publish(msg)

        except sr.WaitTimeoutError:
            # No speech detected, continue listening
            pass
        except sr.UnknownValueError:
            self.get_logger().warn('Could not understand audio')
        except Exception as e:
            self.get_logger().error(f'Error in voice recognition: {e}')
```

#### Visual Processing Pipeline
Implement the computer vision system for object detection and scene understanding:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import numpy as np

class VisualProcessingNode(Node):
    def __init__(self):
        super().__init__('visual_processing_node')
        self.subscription = self.create_subscription(
            Image,
            '/camera/rgb/image_raw',
            self.image_callback,
            10)
        self.object_publisher = self.create_publisher(String, 'detected_objects', 10)
        self.bridge = CvBridge()
        self.get_logger().info('Visual Processing Node Started')

    def image_callback(self, msg):
        try:
            # Convert ROS Image message to OpenCV image
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")

            # Process the image for object detection
            detected_objects = self.detect_objects(cv_image)

            # Publish detected objects
            for obj in detected_objects:
                obj_msg = String()
                obj_msg.data = f"{obj['name']} at ({obj['x']}, {obj['y']})"
                self.object_publisher.publish(obj_msg)

        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')

    def detect_objects(self, image):
        # Simple color-based object detection for demonstration
        # In practice, you'd use YOLO, SSD, or other advanced detectors
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define color ranges for common objects
        color_ranges = {
            'red': ([0, 50, 50], [10, 255, 255]),
            'blue': ([100, 50, 50], [130, 255, 255]),
            'green': ([40, 50, 50], [80, 255, 255])
        }

        detected_objects = []

        for color_name, (lower, upper) in color_ranges.items():
            lower = np.array(lower, dtype="uint8")
            upper = np.array(upper, dtype="uint8")

            mask = cv2.inRange(hsv, lower, upper)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                if cv2.contourArea(contour) > 1000:  # Filter small contours
                    x, y, w, h = cv2.boundingRect(contour)
                    detected_objects.append({
                        'name': color_name,
                        'x': x + w//2,  # Center x
                        'y': y + h//2,  # Center y
                        'width': w,
                        'height': h
                    })

        return detected_objects
```

#### Cognitive Planning Layer
Implement the planning system that combines voice and visual inputs:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Pose
import json

class CognitivePlannerNode(Node):
    def __init__(self):
        super().__init__('cognitive_planner_node')

        # Subscriptions
        self.voice_sub = self.create_subscription(
            String, 'natural_language_command', self.voice_callback, 10)
        self.vision_sub = self.create_subscription(
            String, 'detected_objects', self.vision_callback, 10)

        # Publishers
        self.plan_pub = self.create_publisher(String, 'action_plan', 10)
        self.nav_pub = self.create_publisher(Pose, 'navigation_goal', 10)

        self.current_objects = {}
        self.get_logger().info('Cognitive Planner Node Started')

    def voice_callback(self, msg):
        command = msg.data
        self.get_logger().info(f'Processing command: {command}')

        # Plan based on command and current world state
        plan = self.create_plan(command, self.current_objects)

        # Publish the plan
        plan_msg = String()
        plan_msg.data = json.dumps(plan)
        self.plan_pub.publish(plan_msg)

        self.execute_plan(plan)

    def vision_callback(self, msg):
        # Update current world state with detected objects
        obj_info = msg.data
        # Parse object information and update internal state
        # This is a simplified representation
        self.get_logger().info(f'Updated world state with: {obj_info}')

    def create_plan(self, command, world_state):
        # This is where the LLM integration would happen
        # For now, using simple rule-based planning

        command_lower = command.lower()
        plan = []

        if "move to" in command_lower or "go to" in command_lower:
            # Extract destination
            destination = command_lower.split("to")[-1].strip()
            plan.append({
                "action": "NAVIGATE",
                "target": destination,
                "world_state": world_state
            })

        elif "pick up" in command_lower or "grasp" in command_lower:
            # Extract object to pick up
            obj = command_lower.split("pick up")[-1].split("grasp")[-1].strip()
            plan.append({
                "action": "GRASP",
                "object": obj,
                "world_state": world_state
            })

        elif "place" in command_lower or "put" in command_lower:
            # Extract object and destination
            parts = command_lower.split()
            obj_idx = -1
            for i, part in enumerate(parts):
                if part in ["place", "put"]:
                    obj_idx = i + 1
                    break

            if obj_idx < len(parts):
                obj = parts[obj_idx]
                destination = " ".join(parts[parts.index("on") + 1:]) if "on" in parts else "table"

                plan.extend([
                    {"action": "GRASP", "object": obj, "world_state": world_state},
                    {"action": "NAVIGATE", "target": destination, "world_state": world_state},
                    {"action": "PLACE", "object": obj, "target": destination, "world_state": world_state}
                ])

        return plan

    def execute_plan(self, plan):
        for step in plan:
            action = step["action"]
            if action == "NAVIGATE":
                self.execute_navigation(step)
            elif action == "GRASP":
                self.execute_grasp(step)
            elif action == "PLACE":
                self.execute_place(step)

    def execute_navigation(self, step):
        # Send navigation goal to navigation stack
        self.get_logger().info(f"Navigating to {step['target']}")
        # In a real implementation, this would send navigation goals

    def execute_grasp(self, step):
        # Execute grasping action
        self.get_logger().info(f"Grasping {step['object']}")
        # In a real implementation, this would control the manipulator

    def execute_place(self, step):
        # Execute placing action
        self.get_logger().info(f"Placing {step['object']} at {step['target']}")
        # In a real implementation, this would control the manipulator
```

### Phase 3: System Integration (Week 3)

#### Main Integration Node
Create the main node that coordinates all components:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import threading
import time

class AutonomousHumanoidNode(Node):
    def __init__(self):
        super().__init__('autonomous_humanoid_node')

        # Subscriptions for all components
        self.status_sub = self.create_subscription(
            String, 'system_status', self.status_callback, 10)

        self.command_pub = self.create_publisher(String, 'system_command', 10)

        self.active_components = {
            'voice': False,
            'vision': False,
            'planning': False,
            'navigation': False,
            'manipulation': False
        }

        self.get_logger().info('Autonomous Humanoid System Started')

        # Check system status periodically
        self.create_timer(5.0, self.check_system_status)

    def status_callback(self, msg):
        # Update component status
        status_info = msg.data
        self.get_logger().info(f'System status: {status_info}')

    def check_system_status(self):
        # Check if all required components are active
        all_active = all(self.active_components.values())

        if all_active:
            self.get_logger().info('All systems operational - ready for commands')
        else:
            inactive = [comp for comp, active in self.active_components.items() if not active]
            self.get_logger().warn(f'Inactive components: {inactive}')

def main(args=None):
    rclpy.init(args=args)

    # Start the main system node
    humanoid_node = AutonomousHumanoidNode()

    try:
        rclpy.spin(humanoid_node)
    except KeyboardInterrupt:
        humanoid_node.get_logger().info('Shutting down Autonomous Humanoid System')
    finally:
        humanoid_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

#### Launch File
Create a launch file to start all components together:

```xml
<!-- launch/autonomous_humanoid.launch.py -->
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    return LaunchDescription([
        # Voice Command Node
        Node(
            package='autonomous_humanoid',
            executable='voice_command_node',
            name='voice_command_node',
            output='screen'
        ),

        # Visual Processing Node
        Node(
            package='autonomous_humanoid',
            executable='visual_processing_node',
            name='visual_processing_node',
            output='screen'
        ),

        # Cognitive Planner Node
        Node(
            package='autonomous_humanoid',
            executable='cognitive_planner_node',
            name='cognitive_planner_node',
            output='screen'
        ),

        # Main Integration Node
        Node(
            package='autonomous_humanoid',
            executable='autonomous_humanoid_node',
            name='autonomous_humanoid_node',
            output='screen'
        ),
    ])
```

### Phase 4: Testing and Optimization (Week 4)

#### Testing Scenarios
Create comprehensive tests to validate the system:

```python
#!/usr/bin/env python3
import unittest
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time

class TestAutonomousHumanoid(unittest.TestCase):
    def setUp(self):
        rclpy.init()
        self.node = Node('test_autonomous_humanoid')

        # Create publishers and subscribers for testing
        self.command_publisher = self.node.create_publisher(String, 'natural_language_command', 10)
        self.result_subscriber = self.node.create_subscription(String, 'action_execution_result', self.result_callback, 10)

        self.received_results = []

    def result_callback(self, msg):
        self.received_results.append(msg.data)

    def test_simple_navigation(self):
        """Test basic navigation command"""
        command_msg = String()
        command_msg.data = "Go to the kitchen"
        self.command_publisher.publish(command_msg)

        # Wait for response
        timeout = time.time() + 60.0 * 2  # 2 minutes timeout
        while len(self.received_results) == 0 and time.time() < timeout:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        self.assertGreater(len(self.received_results), 0)
        self.assertIn("NAVIGATE", self.received_results[0])

    def test_object_interaction(self):
        """Test object interaction command"""
        command_msg = String()
        command_msg.data = "Pick up the red cup"
        self.command_publisher.publish(command_msg)

        # Wait for response
        timeout = time.time() + 60.0 * 2  # 2 minutes timeout
        while len(self.received_results) < 2 and time.time() < timeout:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        self.assertGreater(len(self.received_results), 1)
        # Should have detection and grasping actions

    def tearDown(self):
        self.node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    unittest.main()
```

## Performance Evaluation

### Metrics to Track
1. **Command Success Rate**: Percentage of commands executed successfully
2. **Response Time**: Time from command receipt to action completion
3. **System Reliability**: Mean time between failures
4. **User Satisfaction**: Subjective evaluation of system performance

### Evaluation Framework
```python
class PerformanceEvaluator:
    def __init__(self):
        self.commands_executed = 0
        self.commands_successful = 0
        self.total_response_time = 0
        self.start_times = {}

    def start_command_timer(self, command_id):
        self.start_times[command_id] = time.time()

    def end_command_timer(self, command_id, success=True):
        if command_id in self.start_times:
            response_time = time.time() - self.start_times[command_id]
            self.total_response_time += response_time
            self.commands_executed += 1
            if success:
                self.commands_successful += 1
            del self.start_times[command_id]

    def get_success_rate(self):
        if self.commands_executed == 0:
            return 0
        return self.commands_successful / self.commands_executed

    def get_avg_response_time(self):
        if self.commands_executed == 0:
            return 0
        return self.total_response_time / self.commands_executed
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **Voice Recognition Not Working**
   - Check microphone permissions
   - Verify audio input levels
   - Test with simple commands first

2. **Object Detection Failing**
   - Ensure proper lighting conditions
   - Check camera calibration
   - Verify object colors match detection parameters

3. **Navigation Errors**
   - Verify map accuracy
   - Check localization
   - Ensure obstacle detection is working

4. **Planning Failures**
   - Verify all components are communicating
   - Check for ROS 2 topic connections
   - Review LLM prompt effectiveness

## Conclusion

The Autonomous Humanoid capstone project demonstrates the integration of all concepts learned throughout the course. Students have built a complete system that combines:
- Voice recognition for natural interaction
- Computer vision for environmental awareness
- Cognitive planning for decision making
- Robotic control for physical action

This project serves as a foundation for more advanced robotics applications and provides practical experience with complex system integration. The skills developed through this project are directly applicable to real-world robotics challenges.

## Next Steps

After completing this project, consider exploring:
- Advanced perception techniques (3D object detection, SLAM)
- Reinforcement learning for robotic tasks
- Multi-robot coordination
- Human-robot collaboration frameworks