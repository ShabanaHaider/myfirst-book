/**
 * @ts-check
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */

module.exports = {
  tutorialSidebar: [
    {
      type: 'category',
      label: 'Introduction',
      items: [
        'Intro-humanoid-robotics-book/constitution',
        'Intro-humanoid-robotics-book/plan',
        'Intro-humanoid-robotics-book/spec',
        'Intro-humanoid-robotics-book/tasks',
      ],
    },
    {
      type: 'category',
      label: 'Module 1: The Robotic Nervous System (ROS 2)',
      items: [
        'module1-ros2-nervous-system/middleware',
        'module1-ros2-nervous-system/ros2-concepts',
        'module1-ros2-nervous-system/rclpy-bridge',
        'module1-ros2-nervous-system/urdf',
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
        'module4_vla/lesson1-llm-robotics-convergence',
        'module4_vla/lesson2-voice-to-action-whisper',
      ],
    },
  ],
};
