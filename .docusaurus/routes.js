import React from 'react';
import ComponentCreator from '@docusaurus/ComponentCreator';

export default [
  {
    path: '/__docusaurus/debug',
    component: ComponentCreator('/__docusaurus/debug', '5ff'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/config',
    component: ComponentCreator('/__docusaurus/debug/config', '5ba'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/content',
    component: ComponentCreator('/__docusaurus/debug/content', 'a2b'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/globalData',
    component: ComponentCreator('/__docusaurus/debug/globalData', 'c3c'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/metadata',
    component: ComponentCreator('/__docusaurus/debug/metadata', '156'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/registry',
    component: ComponentCreator('/__docusaurus/debug/registry', '88c'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/routes',
    component: ComponentCreator('/__docusaurus/debug/routes', '000'),
    exact: true
  },
  {
    path: '/markdown-page',
    component: ComponentCreator('/markdown-page', '3d7'),
    exact: true
  },
  {
    path: '/docs',
    component: ComponentCreator('/docs', 'fa2'),
    routes: [
      {
        path: '/docs',
        component: ComponentCreator('/docs', '772'),
        routes: [
          {
            path: '/docs',
            component: ComponentCreator('/docs', '953'),
            routes: [
              {
                path: '/docs/intro',
                component: ComponentCreator('/docs/intro', '853'),
                exact: true
              },
              {
                path: '/docs/my-book/Intro-humanoid-robotics-book/constitution',
                component: ComponentCreator('/docs/my-book/Intro-humanoid-robotics-book/constitution', '3cb'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/Intro-humanoid-robotics-book/plan',
                component: ComponentCreator('/docs/my-book/Intro-humanoid-robotics-book/plan', '13e'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/Intro-humanoid-robotics-book/spec',
                component: ComponentCreator('/docs/my-book/Intro-humanoid-robotics-book/spec', '1c7'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/Intro-humanoid-robotics-book/tasks',
                component: ComponentCreator('/docs/my-book/Intro-humanoid-robotics-book/tasks', 'be5'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module1-ros2-nervous-system/middleware',
                component: ComponentCreator('/docs/my-book/module1-ros2-nervous-system/middleware', '462'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module1-ros2-nervous-system/plan',
                component: ComponentCreator('/docs/my-book/module1-ros2-nervous-system/plan', '29c'),
                exact: true
              },
              {
                path: '/docs/my-book/module1-ros2-nervous-system/rclpy-bridge',
                component: ComponentCreator('/docs/my-book/module1-ros2-nervous-system/rclpy-bridge', '1d6'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module1-ros2-nervous-system/ros2-concepts',
                component: ComponentCreator('/docs/my-book/module1-ros2-nervous-system/ros2-concepts', '460'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module1-ros2-nervous-system/spec',
                component: ComponentCreator('/docs/my-book/module1-ros2-nervous-system/spec', 'd59'),
                exact: true
              },
              {
                path: '/docs/my-book/module1-ros2-nervous-system/urdf',
                component: ComponentCreator('/docs/my-book/module1-ros2-nervous-system/urdf', '028'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module2-digital-twin-sim/lesson1-digital-twins',
                component: ComponentCreator('/docs/my-book/module2-digital-twin-sim/lesson1-digital-twins', '658'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module2-digital-twin-sim/lesson2-gazebo',
                component: ComponentCreator('/docs/my-book/module2-digital-twin-sim/lesson2-gazebo', '5dc'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module2-digital-twin-sim/lesson3-unity-hri',
                component: ComponentCreator('/docs/my-book/module2-digital-twin-sim/lesson3-unity-hri', '2a9'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module2-digital-twin-sim/lesson4-sensor-sim',
                component: ComponentCreator('/docs/my-book/module2-digital-twin-sim/lesson4-sensor-sim', 'c7b'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module2-digital-twin-sim/plan',
                component: ComponentCreator('/docs/my-book/module2-digital-twin-sim/plan', '961'),
                exact: true
              },
              {
                path: '/docs/my-book/module2-digital-twin-sim/spec',
                component: ComponentCreator('/docs/my-book/module2-digital-twin-sim/spec', 'c2a'),
                exact: true
              },
              {
                path: '/docs/my-book/module2-digital-twin-sim/tasks',
                component: ComponentCreator('/docs/my-book/module2-digital-twin-sim/tasks', 'b99'),
                exact: true
              },
              {
                path: '/docs/my-book/module3-ai-robot-brain/lesson1-perception-training',
                component: ComponentCreator('/docs/my-book/module3-ai-robot-brain/lesson1-perception-training', '5f0'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module3-ai-robot-brain/lesson2-isaac-sim',
                component: ComponentCreator('/docs/my-book/module3-ai-robot-brain/lesson2-isaac-sim', '52b'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module3-ai-robot-brain/lesson3-isaac-ros-nav',
                component: ComponentCreator('/docs/my-book/module3-ai-robot-brain/lesson3-isaac-ros-nav', '5a1'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module3-ai-robot-brain/lesson4-nav2-path-planning',
                component: ComponentCreator('/docs/my-book/module3-ai-robot-brain/lesson4-nav2-path-planning', '93b'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module3-ai-robot-brain/plan',
                component: ComponentCreator('/docs/my-book/module3-ai-robot-brain/plan', 'e6f'),
                exact: true
              },
              {
                path: '/docs/my-book/module3-ai-robot-brain/spec',
                component: ComponentCreator('/docs/my-book/module3-ai-robot-brain/spec', '5cc'),
                exact: true
              },
              {
                path: '/docs/my-book/module3-ai-robot-brain/tasks',
                component: ComponentCreator('/docs/my-book/module3-ai-robot-brain/tasks', '742'),
                exact: true
              },
              {
                path: '/docs/my-book/module4_vla/lesson1-llm-robotics-convergence',
                component: ComponentCreator('/docs/my-book/module4_vla/lesson1-llm-robotics-convergence', '096'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module4_vla/lesson2-voice-to-action-whisper',
                component: ComponentCreator('/docs/my-book/module4_vla/lesson2-voice-to-action-whisper', 'fa1'),
                exact: true,
                sidebar: "tutorialSidebar"
              },
              {
                path: '/docs/my-book/module4_vla/plan',
                component: ComponentCreator('/docs/my-book/module4_vla/plan', 'ccf'),
                exact: true
              },
              {
                path: '/docs/my-book/module4_vla/spec',
                component: ComponentCreator('/docs/my-book/module4_vla/spec', '19a'),
                exact: true
              },
              {
                path: '/docs/my-book/module4_vla/tasks',
                component: ComponentCreator('/docs/my-book/module4_vla/tasks', 'cb4'),
                exact: true
              },
              {
                path: '/docs/outline',
                component: ComponentCreator('/docs/outline', '339'),
                exact: true
              },
              {
                path: '/docs/tutorial-basics/congratulations',
                component: ComponentCreator('/docs/tutorial-basics/congratulations', '70e'),
                exact: true
              },
              {
                path: '/docs/tutorial-basics/create-a-blog-post',
                component: ComponentCreator('/docs/tutorial-basics/create-a-blog-post', '315'),
                exact: true
              },
              {
                path: '/docs/tutorial-basics/create-a-document',
                component: ComponentCreator('/docs/tutorial-basics/create-a-document', 'f86'),
                exact: true
              },
              {
                path: '/docs/tutorial-basics/create-a-page',
                component: ComponentCreator('/docs/tutorial-basics/create-a-page', '9f6'),
                exact: true
              },
              {
                path: '/docs/tutorial-basics/deploy-your-site',
                component: ComponentCreator('/docs/tutorial-basics/deploy-your-site', 'b91'),
                exact: true
              },
              {
                path: '/docs/tutorial-basics/markdown-features',
                component: ComponentCreator('/docs/tutorial-basics/markdown-features', '272'),
                exact: true
              },
              {
                path: '/docs/tutorial-extras/manage-docs-versions',
                component: ComponentCreator('/docs/tutorial-extras/manage-docs-versions', 'a34'),
                exact: true
              },
              {
                path: '/docs/tutorial-extras/translate-your-site',
                component: ComponentCreator('/docs/tutorial-extras/translate-your-site', '739'),
                exact: true
              }
            ]
          }
        ]
      }
    ]
  },
  {
    path: '/',
    component: ComponentCreator('/', '2e1'),
    exact: true
  },
  {
    path: '*',
    component: ComponentCreator('*'),
  },
];
