from setuptools import setup
import os
from glob import glob

package_name = 'lanbao_core'

setup(
    name=package_name,
    version='0.5.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='揽宝开发团队',
    maintainer_email='dev@lanbao.com',
    description='揽宝核心框架 - 节点基类和公共组件',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'core_node = lanbao_core.core_node:main',
        ],
    },
)
