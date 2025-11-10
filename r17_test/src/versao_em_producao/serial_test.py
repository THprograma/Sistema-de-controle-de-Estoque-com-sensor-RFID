import serial
import time

# Configuração das portas e baud rate
porta1 = "COM5"  # Leitor 1
porta2 = "COM6"  # Leitor 2
baud = 115200

try:
    # Abrindo conexões seriais
    leitor1 = serial.Serial(porta1, baud, timeout=0.5)
#leitor um conectado usando serial.Serial com a porta 1 e baud rate definido
    leitor2 = serial.Serial(porta2, baud, timeout=0.5)
#leitor dois conectado usando serial.Serial com a porta 2 e baud rate definido
    print(f"Conectado às portas {porta1} e {porta2}\n")
#mostra na tela que está conectado às portas definidas
    print("Aproxime uma tag dos leitores... pressione Ctrl+C para sair.\n")

    while True:
        # Lendo dados do leitor 1
        if leitor1.in_waiting > 0:
        #se houver dados esperando para serem lidos no leitor 1
            tag1 = leitor1.readline().decode(errors="ignore").strip()
            #lê uma linha do leitor 1, decodifica e remove espaços em branco
            if tag1:
            #se a tag lida não estiver vazia
                print(f"[Leitor 1] TAG lida -> {tag1}")
                #mostra a tag lida do leitor 1

        # Lendo dados do leitor 2
        if leitor2.in_waiting > 0:
        #se houver dados esperando para serem lidos no leitor 2
            tag2 = leitor2.readline().decode(errors="ignore").strip()
            #lê uma linha do leitor 2, decodifica e remove espaços em branco
            if tag2:
            #se a tag lida não estiver vazia
                print(f"[Leitor 2] TAG lida -> {tag2}")
                #mostra a tag lida do leitor 2

        time.sleep(0.05)  # Pequena pausa para não sobrecarregar a CPU

except serial.SerialException as e:
#exceção para erros na porta serial
    print(f"Erro ao abrir porta serial: {e}")
#mostra o erro ocorrido ao tentar abrir a porta serial
except KeyboardInterrupt:
# captura a interrupção do usuário (Ctrl+C)
    print("\nEncerrado pelo usuário.")
#mostra mensagem de encerramento
finally:
    # Fechando as portas
    leitor1.close()
    leitor2.close()