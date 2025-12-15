# Cognitive Planning Using LLMs

This lesson demonstrates how Large Language Models (LLMs) can be used to translate natural language instructions into executable ROS 2 action sequences. Students will learn how to bridge high-level human commands with low-level robotic behaviors.

## Learning Objectives
By the end of this lesson, students will be able to:
- Understand the concept of cognitive planning in robotics
- Map natural language commands to ROS 2 action sequences
- Implement a basic LLM-based planner for robotic tasks
- Integrate LLM outputs with ROS 2 services and actions
- Handle planning failures and recovery strategies

## Introduction to Cognitive Planning

Cognitive planning in robotics refers to the process of translating high-level goals or natural language commands into sequences of executable actions. This is a crucial capability for autonomous robots that need to interact with humans in natural ways.

Traditional robotics approaches require pre-programmed behaviors for specific tasks. Cognitive planning allows robots to understand and execute novel commands by reasoning about their environment and capabilities.

## Natural Language to Action Mapping

The process of converting natural language to robot actions involves several steps:

1. **Parsing**: Breaking down the natural language command to extract key elements
2. **Entity Recognition**: Identifying objects, locations, and actions mentioned in the command
3. **Intent Classification**: Determining what the user wants the robot to do
4. **Action Sequence Generation**: Creating a sequence of ROS 2 actions to accomplish the goal

### Example Command Processing

Let's consider a simple command: "Move to the kitchen and pick up the red cup."

- **Parsed Command**: Move → Location: kitchen → Action: pick up → Object: red cup
- **Entity Recognition**:
  - Location: kitchen (known location in robot's map)
  - Object: red cup (object with color=red and type=cup)
  - Action: pick up (manipulation action)
- **Action Sequence**:
  1. Navigate to kitchen location
  2. Search for red cup in the vicinity
  3. Approach the red cup
  4. Grasp the red cup

## LLM Integration with ROS 2

Large Language Models can serve as the cognitive layer that interprets natural language and generates action sequences. Here's how to integrate LLMs with ROS 2:

### Setting up the LLM Interface

```python
import openai
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Pose

class CognitivePlannerNode(Node):
    def __init__(self):
        super().__init__('cognitive_planner')
        self.subscription = self.create_subscription(
            String,
            'natural_language_command',
            self.command_callback,
            10)
        self.get_logger().info('Cognitive Planner Node Started')

    def command_callback(self, msg):
        # Process the natural language command using LLM
        action_sequence = self.generate_action_sequence(msg.data)
        # Execute the action sequence
        self.execute_action_sequence(action_sequence)
```

### Prompt Engineering for Robotic Planning

The key to effective cognitive planning is crafting the right prompts for the LLM:

```
You are a cognitive planning assistant for a humanoid robot. Your task is to convert natural language commands into sequences of ROS 2 actions.

The available actions are:
- NAVIGATE_TO(location): Navigate the robot to a specific location
- DETECT_OBJECT(object_type): Search for an object of a specific type
- APPROACH_OBJECT(object_id): Move closer to a specific object
- GRASP_OBJECT(object_id): Grasp/pick up an object
- PLACE_OBJECT(location): Place an object at a location
- SPEAK(text): Make the robot speak text

Convert the following command into a sequence of actions:
Command: "{user_command}"
Output: ["ACTION1(parameters)", "ACTION2(parameters)", ...]
```

## Practical Implementation

Let's implement a simple cognitive planner that can handle basic commands:

### Step 1: Environment Setup

First, ensure you have the required dependencies:

```bash
pip install openai rospy
```

### Step 2: Basic Planner Implementation

```python
import openai
import json
from typing import List, Dict

class SimpleCognitivePlanner:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        self.action_mapping = {
            "NAVIGATE_TO": self.navigate_to,
            "DETECT_OBJECT": self.detect_object,
            "APPROACH_OBJECT": self.approach_object,
            "GRASP_OBJECT": self.grasp_object,
            "PLACE_OBJECT": self.place_object,
            "SPEAK": self.speak
        }

    def generate_action_sequence(self, command: str) -> List[Dict]:
        prompt = f"""
        You are a cognitive planning assistant for a humanoid robot. Convert the following natural language command into a sequence of ROS 2 actions.

        Available actions:
        - NAVIGATE_TO(location): Navigate to a location
        - DETECT_OBJECT(object_type): Detect an object
        - APPROACH_OBJECT(object_id): Approach an object
        - GRASP_OBJECT(object_id): Grasp an object
        - PLACE_OBJECT(location): Place an object
        - SPEAK(text): Speak text

        Command: {command}
        Output only the JSON array of actions:
        """

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=200,
            temperature=0.1
        )

        try:
            actions = json.loads(response.choices[0].text.strip())
            return actions
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return self.fallback_parse(command)

    def execute_action_sequence(self, actions: List[Dict]):
        for action in actions:
            action_name = action['action']
            params = action.get('params', {})
            if action_name in self.action_mapping:
                self.action_mapping[action_name](**params)

    def fallback_parse(self, command: str) -> List[Dict]:
        # Simple fallback parser for basic commands
        command_lower = command.lower()
        actions = []

        if "move to" in command_lower or "go to" in command_lower:
            # Extract location
            location = command_lower.split("to")[-1].strip()
            actions.append({"action": "NAVIGATE_TO", "params": {"location": location}})

        if "pick up" in command_lower or "grasp" in command_lower:
            # Extract object
            obj = command_lower.split("pick up")[-1].split("grasp")[-1].strip()
            actions.append({"action": "GRASP_OBJECT", "params": {"object_id": obj}})

        return actions

    # Placeholder implementations for robot actions
    def navigate_to(self, location: str):
        print(f"Navigating to {location}")
        # In a real implementation, this would send navigation goals to ROS 2

    def detect_object(self, object_type: str):
        print(f"Detecting {object_type}")
        # In a real implementation, this would use perception nodes

    def approach_object(self, object_id: str):
        print(f"Approaching {object_id}")
        # In a real implementation, this would move the robot closer to the object

    def grasp_object(self, object_id: str):
        print(f"Grasping {object_id}")
        # In a real implementation, this would control the robot's gripper

    def place_object(self, location: str):
        print(f"Placing object at {location}")
        # In a real implementation, this would place the object

    def speak(self, text: str):
        print(f"Speaking: {text}")
        # In a real implementation, this would use text-to-speech
```

## Advanced Topics

### Multi-step Planning
For complex tasks, the planner needs to maintain context and plan multiple steps ahead, considering the robot's current state and the expected outcomes of each action.

### Handling Uncertainty
Robots operate in uncertain environments. The cognitive planner should include mechanisms for:
- Handling failed actions
- Replanning when initial plans fail
- Incorporating sensor feedback to update plans

### Context and Memory
Advanced cognitive planners maintain context about:
- Previous commands and their outcomes
- Current robot state
- Environmental state
- User preferences and history

## Hands-on Exercise

Create a cognitive planner that can handle the following commands:
1. "Go to the table and bring me the blue pen"
2. "Move to the living room and wait there"
3. "Find the book and place it on the shelf"

Test your planner with various natural language commands and verify that it generates appropriate action sequences.

## Summary

Cognitive planning using LLMs represents a significant advancement in human-robot interaction, allowing robots to understand and execute natural language commands. By combining LLMs with ROS 2, we can create more intuitive and flexible robotic systems that can adapt to novel tasks without requiring explicit programming for each scenario.