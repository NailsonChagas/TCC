% 1. Parâmetros de amostragem (F_sim = 5 kHz * 100 = 500 kHz)
Fs = 500e3;              % Frequência de amostragem (Hz)
Ts = 1 / Fs;             % Período de amostragem (2 us)

% 2. Função de Transferência Contínua H(s)
num_s = [9.87e6];
den_s = [1, 5441, 9.87e6];
Hs = tf(num_s, den_s);

% 3. Discretização via Bilinear (Tustin)
Hz = c2d(Hs, Ts, 'tustin');

% 4. Extração dos Coeficientes do Polinômio Discreto H(z)
[num_z, den_z] = tfdata(Hz, 'v');

% Normalização garantindo a0 = 1 (Forma Direta I)
b0 = num_z(1);
b1 = num_z(2);
b2 = num_z(3);
a1 = den_z(2); % Notação padrão H(z) = (b0 + b1*z^-1 + b2*z^-2)/(1 + a1*z^-1 + a2*z^-2)
a2 = den_z(3);

% 5. Exibição formatada para o firmware em C
fprintf('\n================ COEFICIENTES PARA O FIRMWARE C ================\n');
fprintf('const float b0 = %22.16ff;\n', b0);
fprintf('const float b1 = %22.16ff;\n', b1);
fprintf('const float b2 = %22.16ff;\n', b2);
fprintf('const float a1 = %22.16ff;\n', a1);
fprintf('const float a2 = %22.16ff;\n', a2);
fprintf('=================================================================\n\n');

% 6. Validação Visual: Comparação dos Diagramas de Bode (Contínuo vs Discreto)
figure;
bode(Hs, 'r', Hz, 'b--');
grid on;
legend('H(s) - Contínuo', 'H(z) - Discreto (500 kHz)');
title('Comparação da Resposta em Frequência (Bilinear)');