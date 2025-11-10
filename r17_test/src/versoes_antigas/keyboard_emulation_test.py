import time

print("Teste de Emulação de Teclado - R17-A")
print("Abra um editor de texto ou mantenha este terminal em foco.")
print("Aproxime a tag do leitor. Pressione Ctrl+C para sair.\n")

try:
    while True:
        # usa input() — o leitor 'digita' o código e normalmente envia Enter, o que completa input()
        codigo = input()  # quando o leitor emula teclado, ele 'digita' e envia Enter
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        if codigo.strip() != "":
            print(f"[{ts}] TAG lida: {codigo.strip()}")
except KeyboardInterrupt:
    print("\nSaindo do teste.")