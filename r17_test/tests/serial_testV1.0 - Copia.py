import serial

porta = "COM5"  # ajuste se necessário
baud = 115200     # padrão da maioria dos leitores UHF

try:
    ser = serial.Serial(porta, baud, timeout=1)
    print(f"Conectado à porta {porta} ({baud} baud)")    
    print("Aproxime uma tag UHF... pressione Ctrl+C para sair.\n")

    while True:
        if ser.in_waiting > 0:
            dados = ser.readline().decode(errors="ignore").strip()
            if dados:
                print(f"TAG lida -> {dados}")

except serial.SerialException:
    print("Erro: não foi possível abrir a porta serial.")
except KeyboardInterrupt:
    print("\nEncerrado pelo usuário.")