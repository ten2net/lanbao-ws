from setuptools import setup

package_name = 'lanbao_strategy'

setup(
    name=package_name,
    version='0.5.0',
    packages=[package_name, f'{package_name}.strategies'],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='揽宝开发团队',
    maintainer_email='dev@lanbao.com',
    description='揽宝策略服务 - 策略模板和策略管理',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'strategy_manager_node = lanbao_strategy.strategy_manager_node:main',
        ],
    },
)
