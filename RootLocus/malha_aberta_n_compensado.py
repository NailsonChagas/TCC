import matplotlib.pyplot as plt
import control as ct

from aux_graph import plot_root_locus_matlab, plot_specification_region

s = ct.TransferFunction.s

G = 1.984e11 / (s**2 + 1.332e5*s + 3.968e9) # Planta (Buck CCM)
H = 9.87e8 / (s**2 + 5.441e4*s + 9.87e8) # Filtro antialiasing
L_uncompensated = G * H # Malha aberta não compensada

print(f"Planta G(s): {G}")
print(f"\nFiltro H(s): {H}")
print(f"\nMalha aberta L(s): {L_uncompensated}")

fig, ax = plot_root_locus_matlab(L_uncompensated)
plot_specification_region(ax, zeta_min=0.69,sigma_min=7.997e3)
fig.savefig('lr_n_compensado_com_região.png', dpi=400, bbox_inches='tight')
plt.show()
plt.close('all')

fig, ax = plot_root_locus_matlab(L_uncompensated)
fig.savefig('lr_n_compensado.png', dpi=400, bbox_inches='tight')
plt.show()