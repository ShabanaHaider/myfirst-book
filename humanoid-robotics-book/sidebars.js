/**
 * @ts-check
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */

module.exports = {
  tutorialSidebar: [
    {
      type: 'category',
      label: 'Module 1: The Robotic Nervous System (ROS 2)',
      items: [
        'module1-ros2/middleware',
        'module1-ros2/ros2-concepts',
        'module1-ros2/rclpy-bridge',
        'module1-ros2/urdf',
      ],
    },
    {
      type: 'category',
      label: 'Module 2: The Digital Twin (Gazebo & Unity)',
      items: [
        'module2-digital-twin-sim/lesson1-digital-twins',
        'module2-digital-twin-sim/lesson2-gazebo',
        'module2-digital-twin-sim/lesson3-unity-hri',
        'module2-digital-twin-sim/lesson4-sensor-sim',
      ],
    },
    {
      type: 'category',
      label: 'Module 3: The AI-Robot Brain (NVIDIA Isaac™)',
      items: [
        'module3-ai-robot-brain/lesson1-perception-training',
        'module3-ai-robot-brain/lesson2-isaac-sim',
        'module3-ai-robot-brain/lesson3-isaac-ros-nav',
        'module3-ai-robot-brain/lesson4-nav2-path-planning',
      ],
    },
    {
      type: 'category',
      label: 'Module 4: Vision-Language-Action (VLA)',
      items: [
        'module4-vision-language-action/lesson1-llm-robotics-convergence',
        'module4-vision-language-action/lesson2-voice-to-action-whisper',
        'module4-vision-language-action/lesson3-cognitive-planning-llms',
        'module4-vision-language-action/lesson4-capstone-autonomous-humanoid',
      ],
    },
  ],
};

