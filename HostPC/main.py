from models.BuckConverterCCM import BuckConverterCCM
from models.SimulatorTest import SimulatorTest

buck = BuckConverterCCM.from_design_parameters(
    Vs=30,
    Vo=20,
    Po=15,
    delta_iL=0.5,
    delta_Vo=0.1,
)

print(buck)

test = SimulatorTest(
    converter=buck,
    amplitude=1,
    frequency=60,
)

print(test)
print(test.sine_table)