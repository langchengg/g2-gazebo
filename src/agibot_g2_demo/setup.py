from glob import glob
from setuptools import find_packages, setup

package_name = 'agibot_g2_demo'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test', 'test.*']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml') + glob('config/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=False,
    maintainer='Lang Cheng',
    maintainer_email='lang.cheng@student.manchester.ac.uk',
    description='Python ROS 2 application for Agibot G2 arm motion and joint telemetry in Gazebo simulation.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'sayHello = agibot_g2_demo.say_hello_node:main',
        'telemetry = agibot_g2_demo.telemetry_node:main',
    ]},
)
