#!/bin/bash
set -e

echo "=== ChronoPersona Repository Initialization ==="

# 创建 chronopersona 包目录结构
mkdir -p chronopersona/{contracts/{interfaces,schemas,openapi},agent_core/{nodes,emotion_engine},memory_system/{l0_crdt,l1_working,l2_episodic,l3_semantic,retrieval},embodied/adapters,persona_engine/templates,model_router,evaluation,mocks,frontend}

# 创建根目录下的独立目录
mkdir -p tests

# 创建 Python 包标记文件
touch chronopersona/__init__.py
touch chronopersona/contracts/__init__.py
touch chronopersona/contracts/interfaces/__init__.py
touch chronopersona/contracts/schemas/__init__.py
touch chronopersona/agent_core/__init__.py
touch chronopersona/agent_core/nodes/__init__.py
touch chronopersona/memory_system/__init__.py
touch chronopersona/memory_system/l0_crdt/__init__.py
touch chronopersona/memory_system/l1_working/__init__.py
touch chronopersona/memory_system/l2_episodic/__init__.py
touch chronopersona/memory_system/l3_semantic/__init__.py
touch chronopersona/memory_system/retrieval/__init__.py
touch chronopersona/embodied/__init__.py
touch chronopersona/persona_engine/__init__.py
touch chronopersona/model_router/__init__.py
touch chronopersona/evaluation/__init__.py
touch chronopersona/mocks/__init__.py
touch tests/__init__.py

echo "=== Directory structure created ==="
echo "Next steps:"
echo "  1. pip install -r requirements.txt"
echo "  2. Configure API keys in .env"
echo "  3. Run: aider --model deepseek/deepseek-chat --architect --read AIDER.md --read CLAUDE.md"