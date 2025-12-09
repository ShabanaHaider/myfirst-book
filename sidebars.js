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
        'my-book/Intro-humanoid-robotics-book/constitution',
        'my-book/Intro-humanoid-robotics-book/plan',
        'my-book/Intro-humanoid-robotics-book/spec',
        'my-book/Intro-humanoid-robotics-book/tasks',
      ],
    },
    {
      type: 'category',
      label: 'Module 1: The Robotic Nervous System (ROS 2)',
      items: [
        'my-book/module1-ros2-nervous-system/middleware',
        'my-book/module1-ros2-nervous-system/ros2-concepts',
        'my-book/module1-ros2-nervous-system/rclpy-bridge',
        'my-book/module1-ros2-nervous-system/urdf',
      ],
    },
    {
      type: 'category',
      label: 'Module 2: The Digital Twin (Gazebo & Unity)',
      items: [
        'my-book/module2-digital-twin-sim/lesson1-digital-twins',
        'my-book/module2-digital-twin-sim/lesson2-gazebo',
        'my-book/module2-digital-twin-sim/lesson3-unity-hri',
        'my-book/module2-digital-twin-sim/lesson4-sensor-sim',
      ],
    },
    {
      type: 'category',
      label: 'Module 3: The AI-Robot Brain (NVIDIA Isaac™)',
      items: [
        'my-book/module3-ai-robot-brain/lesson1-perception-training',
        'my-book/module3-ai-robot-brain/lesson2-isaac-sim',
        'my-book/module3-ai-robot-brain/lesson3-isaac-ros-nav',
        'my-book/module3-ai-robot-brain/lesson4-nav2-path-planning',
      ],
    },
    {
      type: 'category',
      label: 'Module 4: Vision-Language-Action (VLA)',
      items: [
        'my-book/module4_vla/lesson1-llm-robotics-convergence',
        'my-book/module4_vla/lesson2-voice-to-action-whisper',
      ],
    },
  ],
};
