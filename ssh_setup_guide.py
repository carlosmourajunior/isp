#!/usr/bin/env python3
"""
Guia completo para configurar múltiplas chaves SSH
"""

print("🔐 CONFIGURAÇÃO DE MÚLTIPLAS CHAVES SSH - CONCLUÍDA!")
print("=" * 60)

print("\n📋 RESUMO DO QUE FOI FEITO:")
print("✅ 1. Chave SSH existente identificada: id_ed25519")
print("✅ 2. Nova chave SSH gerada: id_ed25519_repo2")
print("✅ 3. Arquivo SSH config criado")

print("\n🔑 SUA NOVA CHAVE PÚBLICA:")
print("-" * 40)
with open(r"C:\Users\carlos_remoto\.ssh\id_ed25519_repo2.pub", "r") as f:
    public_key = f.read().strip()
    print(public_key)

print("\n🚀 PRÓXIMOS PASSOS:")
print("1. Copie a chave pública acima")
print("2. Acesse: https://github.com/settings/ssh/new")
print("3. Cole a chave e dê um título (ex: 'Chave Repo2')")
print("4. Clique em 'Add SSH key'")

print("\n💡 COMO USAR AS DIFERENTES CHAVES:")

print("\n🔹 Para o repositório atual (isp):")
print("   git clone git@github.com:carlosmourajunior/isp.git")
print("   git remote set-url origin git@github.com:carlosmourajunior/isp.git")

print("\n🔹 Para o novo repositório:")
print("   git clone git@github-repo2:usuario/repo.git")
print("   git remote set-url origin git@github-repo2:usuario/repo.git")

print("\n⚙️ ARQUIVO SSH CONFIG CRIADO:")
print("   Localização: C:\\Users\\carlos_remoto\\.ssh\\config")
print("   Configurado para usar diferentes chaves automaticamente")

print("\n🔧 COMANDOS ÚTEIS:")
print("   # Testar conexão com chave padrão")
print("   ssh -T git@github.com")
print("")
print("   # Testar conexão com nova chave")
print("   ssh -T git@github-repo2")
print("")
print("   # Ver chaves disponíveis")
print("   ls C:\\Users\\carlos_remoto\\.ssh\\*.pub")

print("\n📝 EXEMPLO DE USO:")
print("   # Clone com chave padrão")
print("   git clone git@github.com:carlosmourajunior/meu-repo.git")
print("")
print("   # Clone com nova chave")
print("   git clone git@github-repo2:outro-usuario/outro-repo.git")

print("\n🎯 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
print("Agora você pode usar múltiplas chaves SSH no mesmo computador!")