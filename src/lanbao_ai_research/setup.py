from setuptools import setup

package_name = 'lanbao_ai_research'

setup(
    name=package_name,
    version='0.5.0',
    packages=[package_name, f'{package_name}.agents', f'{package_name}.llm',
              f'{package_name}.llm.providers', f'{package_name}.data_client'],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='揽宝开发团队',
    maintainer_email='dev@lanbao.com',
    description='揽宝智能投研分析模块',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ai_research_node = lanbao_ai_research.ai_research_node:main',
        ],
    },
)
