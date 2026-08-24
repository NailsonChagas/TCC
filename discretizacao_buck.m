% Limpeza de workspace e command window
clear; clc;

% Declaração das variáveis simbólicas
syms R L C Tsim real
syms iLk vcK iL_kp1 vc_kp1 vsK vs_kp1 real

% Vetores de estado
Xk = [iLk; vcK];
X_kp1 = [iL_kp1; vc_kp1]; % Usado apenas para a exibição final

% Matriz Identidade 2x2
I = eye(2);

%% =================================================================
% DEFINIÇÃO DO SISTEMA CONTÍNUO
% ==================================================================

% Estado 1 (Chave Fechada)
A1 = [  0,   -1/L; 
      1/C, -1/(R*C)];
B1 = [1/L; 
        0];

% Estado 2 (Chave Aberta)
A2 = [  0,   -1/L; 
      1/C, -1/(R*C)];
B2 = [  0; 
        0];

%% =================================================================
% 1. DISCRETIZAÇÃO MATRICIAL - MÉTODO DE EULER (Forward)
% Ad = I + Tsim*A
% Bd = Tsim*B
% ==================================================================

% --- ESTADO 1 (CHAVE FECHADA) ---
Ad1_euler = simplify(I + Tsim * A1);
Bd1_euler = simplify(Tsim * B1);

% Equação: x[k+1] = Ad*x[k] + Bd*u[k]
X_kp1_euler_1 = simplify(Ad1_euler * Xk + Bd1_euler * vsK);

% --- ESTADO 2 (CHAVE ABERTA) ---
Ad2_euler = simplify(I + Tsim * A2);
Bd2_euler = simplify(Tsim * B2);

X_kp1_euler_2 = simplify(Ad2_euler * Xk + Bd2_euler * vsK);


%% =================================================================
% 2. DISCRETIZAÇÃO MATRICIAL - MÉTODO DO TRAPÉZIO (Tustin)
% ==================================================================
% COMO A DEPENDÊNCIA DOS VALORES FUTUROS (k+1) É ELIMINADA?
%
% O método do Trapézio é implícito. A equação inicial possui x[k+1] 
% dos dois lados da igualdade:
% (x[k+1] - x[k])/Tsim = A*(x[k+1] + x[k])/2 + B*(u[k+1] + u[k])/2
%
% Para "desacoplar" e isolar x[k+1], o MATLAB fará os seguintes passos
% matemáticos através de matrizes:
%
% Passo 1: Multiplica por Tsim e agrupa tudo de k+1 na esquerda e k na direita:
% x[k+1] - (Tsim/2)*A*x[k+1] = x[k] + (Tsim/2)*A*x[k] + (Tsim/2)*B*(u[k+1]+u[k])
%
% Passo 2: Fatora usando a Matriz Identidade (I):
% (I - (Tsim/2)*A) * x[k+1] = (I + (Tsim/2)*A) * x[k] + (Tsim/2)*B*(u[k+1]+u[k])
%
% Passo 3: Isola x[k+1] multiplicando pela INVERSA de (I - (Tsim/2)*A):
% x[k+1] = inv(I - (Tsim/2)*A) * [(I + (Tsim/2)*A)*x[k] + (Tsim/2)*B*(u[k+1]+u[k])]
%
% RESULTADO: O x[k+1] fica isolado. Os estados futuros são "absorvidos" 
% no cálculo das matrizes Ad e Bd. As linhas abaixo executam isso:
% ==================================================================

% --- ESTADO 1 (CHAVE FECHADA) ---
% Calcula a matriz inversa responsável por isolar x[k+1]
Inv_M1 = inv(I - (Tsim/2) * A1);

% Calcula as matrizes discretas já sem loop algébrico
Ad1_trap = simplify(Inv_M1 * (I + (Tsim/2) * A1));
Bd1_trap = simplify(Inv_M1 * (Tsim/2) * B1);

% Equação final: x[k+1] = Ad*x[k] + Bd*(u[k+1] + u[k])
X_kp1_trap_1 = simplify(Ad1_trap * Xk + Bd1_trap * (vs_kp1 + vsK));


% --- ESTADO 2 (CHAVE ABERTA) ---
Inv_M2 = inv(I - (Tsim/2) * A2);

Ad2_trap = simplify(Inv_M2 * (I + (Tsim/2) * A2));
Bd2_trap = simplify(Inv_M2 * (Tsim/2) * B2);

X_kp1_trap_2 = simplify(Ad2_trap * Xk + Bd2_trap * (vs_kp1 + vsK));


%% =================================================================
% 3. EXIBIÇÃO DAS EQUAÇÕES DE DIFERENÇA FINAIS
% ==================================================================

fprintf('\n=======================================================\n');
fprintf(' EQUAÇÕES DE DIFERENÇA (GERADAS VIA MATRIZES) \n');
fprintf('=======================================================\n');

% Montando as equações de igualdade (linha por linha) para exibição
eq_iL_euler_1 = iL_kp1 == X_kp1_euler_1(1);
eq_vc_euler_1 = vc_kp1 == X_kp1_euler_1(2);

eq_iL_euler_2 = iL_kp1 == X_kp1_euler_2(1);
eq_vc_euler_2 = vc_kp1 == X_kp1_euler_2(2);

eq_iL_trap_1  = iL_kp1 == X_kp1_trap_1(1);
eq_vc_trap_1  = vc_kp1 == X_kp1_trap_1(2);

eq_iL_trap_2  = iL_kp1 == X_kp1_trap_2(1);
eq_vc_trap_2  = vc_kp1 == X_kp1_trap_2(2);


% --- IMPRESSÃO EULER ---
fprintf('\n>>> MÉTODO DE EULER - ESTADO 1 (CHAVE FECHADA) <<<\n');
pretty(eq_iL_euler_1);
pretty(eq_vc_euler_1);

fprintf('\n>>> MÉTODO DE EULER - ESTADO 2 (CHAVE ABERTA) <<<\n');
pretty(eq_iL_euler_2);
pretty(eq_vc_euler_2);


% --- IMPRESSÃO TRAPÉZIO ---
fprintf('\n>>> MÉTODO DO TRAPÉZIO - ESTADO 1 (CHAVE FECHADA) <<<\n');
pretty(eq_iL_trap_1);
pretty(eq_vc_trap_1);

fprintf('\n>>> MÉTODO DO TRAPÉZIO - ESTADO 2 (CHAVE ABERTA) <<<\n');
pretty(eq_iL_trap_2);
pretty(eq_vc_trap_2);


