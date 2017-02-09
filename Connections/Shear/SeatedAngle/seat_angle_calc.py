'''
Created on 2-Sept-2016
@author: jayant patil
'''

''' 
References:

Design of Steel Structures (DoSS) - N. Subramanian
First published 2008, 14th impression 2014
    Chapter 5: Bolted Connections
    Example 5.14, Page 406

IS 800: 2007
    General construction in steel - Code of practice (Third revision)

ASCII diagram

            +-+-------------+-+   +-------------------------+
            | |             | |   |-------------------------|
            | |             | |   |                         |
            | |             | |   |                         |
            | |             | |   |                         |
            | |             | |   |                         |
            | |             | |   |-------------------------|
            | |             | |   +-------------------------+
            | |             | |+-----------+
            | |             | || +---------+
            | |             | || |
            | |         +---|-||-|---+
            | |         +---|-||-|---+
            | |             | || |
            | |         +---|-||-|---+
            | |         +---|-||-|---+
            | |             | ||_|
            | |             | |
            | |             | |
            +-+-------------+-+

'''

import math
import logging
from model import get_angledata, get_beamdata, get_columndata, module_setup
from PyQt4.Qt import QString
from Connections.connection_calculations import ConnectionCalculations

logger = logging.getLogger("osdag.SeatAngleCalc")

# TODO add input validation to select only angles which can accommodate 2 lines of bolts
# TODO check reduction factors for bolt group capacity
# TODO remove smaller bolt diameters from possible inputs
# TODO bolts_provided and bolts_required in UI and output_dict
# TODO pitch and gauge rounding off issues
# TODO incorrect pitch calcs.
# TODO sum of edge_dist+gauge*(num_cols-1)+edge_dist != angle_l due to rounding off
# TODO overwrite calculated top angle if user selects other top angle in GUI
# TODO implement 6 mm as min seat angle thickness
# TODO - DONE moment capacity of outstanding leg based elastic moment capacity
#

class SeatAngleCalculation(ConnectionCalculations):
    """Perform design and detailing checks for seated angle connection.

    Attributes:
        gamma_mb (float): partial safety factor for material - resistance of connection - bolts
        gamma_m0 (float): partial safety factor for material - resistance governed by yielding or buckling
        gamma_m1 (float): partial safety factor for material - resistance governed by ultimate stress
        bolt_hole_type (boolean): bolt hole type - 1 for standard; 0 for oversize
        custom_hole_clearance (float): user defined hole clearance, if any
        beam_col_clear_gap (int): clearance + tolerance
        min_edge_multiplier (float): multipler for min edge distance check - based on edge type
        root_clearance (int): clearance of bolt row from the root of seated angle

        top_angle (string)
        connectivity (string)
        beam_section (string)
        column_section (string)
        beam_fu (float)
        beam_fy (float)
        column_fu (float)
        column_fy (float)
        angle_fy (float)
        angle_fu (float)
        shear_force (float)
        bolt_diameter (int)
        bolt_type (string)
        bolt_grade (float)
        bolt_fu (int)
        bolt_diameter (int)
        bolt_hole_diameter (int)
        angle_sec
        dict_angle_data = model.get_angledata(angle_sec)
        beam_w_t (float): beam web thickness
        beam_f_t (float): beam flange thickness
        beam_d  (float): beam depth
        beam_w_f  (float): beam width
        beam_R1 (float): beam root radius
        column_f_t (float): column flange thickness
        column_d (float): column depth
        column_w_f (float): column width
        column_R1 (float): column root radius
        angle_t (float): angle thickness
        angle_A  (float): longer leg of unequal angle
        angle_B  (float): shorter leg of unequal angle
        angle_R1 (float)
        angle_l (float)

        safe (Boolean) : status of connection, True if safe
        output_dict (dictionary)

        moment_at_root_angle (float)
        moment_capacity_angle (float): Moment capacity of outstanding lege of the seated angle
        is_shear_high (boolean): denotes if the shear fails in high shear [Cl 8.2.1]
        moment_high_shear_beta (float): factor for moment capacity with high shear
        leg_moment_d (float): M_d
        outstanding_leg_shear_capacity (float)
        beam_shear_strength (float)
        bolt_shear_capacity (float)
        k_b (float)
        bolt_bearing_capacity (float)
        bolt_value (float)
        bolt_group_capacity (float)
        bolts_required (int)
        num_rows (int)
        num_cols (int)
        pitch (float)
        gauge (float)
        min_end_dist (int)
        min_edge_dist (int)
        min_pitch (int)
        min_gauge (int)
        end_dist (int)
        edge_dist (int)
        pitch (float)
        gauge (float)
        max_spacing (int)
        max_edge_dist (int)

    """

    def __init__(self):
        """Initialize all attributes."""
        self.max_spacing = 0.0
        self.gamma_mb = 0.0
        self.gamma_m0 = 0.0
        self.gamma_m1 = 0.0
        self.bolt_hole_type = 1
        self.custom_hole_clearance = None
        self.beam_col_clear_gap = 0
        self.min_edge_multiplier = 1
        self.root_clearance = 0
        self.top_angle = ""
        self.connectivity = ""
        self.beam_section = ""
        self.column_section = ""
        self.beam_fu = 0
        self.beam_fy = 0
        self.column_fu = 0
        self.column_fy = 0
        self.angle_fy = 0
        self.angle_fu = 0
        self.shear_force = 0.0
        self.bolt_diameter = 1
        self.bolt_type = 1
        self.bolt_grade = ""
        self.bolt_fu = 0
        self.bolt_diameter = 1
        self.bolt_hole_diameter = 1
        self.angle_sec = ""
        self.dict_angle_data = {}
        self.beam_w_t = 1
        self.beam_f_t = 1
        self.beam_d = 1
        self.beam_w_f = 1
        self.beam_R1 = 1
        self.column_f_t = 1
        self.column_d = 1
        self.column_w_f = 1
        self.column_R1 = 1
        self.angle_t = 1
        self.angle_A = 1
        self.angle_B = 1
        self.angle_R1 = 1
        self.angle_l = 1

        self.safe = True
        self.output_dict = {}

        self.moment_at_root_angle =  0.0
        self.moment_capacity_angle =  0.0
        self.is_shear_high = False
        self.leg_moment_d = 0.0
        self.moment_high_shear_beta = 0.0
        self.outstanding_leg_shear_capacity =  0.0
        self.beam_shear_strength = 0.0
        self.bolt_shear_capacity =  0.0
        self.k_b =  0.0
        self.bolt_bearing_capacity =  0.0
        self.bolt_value =  0.0
        self.bolt_group_capacity =  0.0
        self.bolts_required = 1
        self.num_rows = 1
        self.num_cols = 1
        self.pitch = 1
        self.gauge = 1
        self.min_end_dist = 1
        self.min_edge_dist = 1
        self.min_pitch = 1
        self.min_gauge = 1
        self.end_dist = 1
        self.edge_dist = 1
        self.pitch = 1
        self.gauge = 1
        self.max_spacing = 1
        self.max_edge_dist = 1

    def top_angle_section(self):
        """Identify appropriate top angle size based on beam depth.

        Args:
            none

        Returns:
            top_angle(string): top angle section

        Note:
            Assumptions:
                Calculating top angle dimensions based on thumb rules:
                    top_angle_side = beam_depth/4
                    top_angle_thickness = top_angle_side/10
                Select the nearest available equal angle as the top angle.
                Equal angles satisfying both these thumb rules are selected for this function from steel tables
        """
        try:
            # minimum length of leg of top angle is twice edge distance + angle thickness.
            # as the side length is rounded up in the next step, ignoring angle thickness while calculating
            # minimum length of side
            top_angle_side_minimum = 2 * 1.5 * self.bolt_hole_diameter # twice edge distance
            top_angle_side = max(self.beam_d/4, top_angle_side_minimum)
            # round up to nearest 5 mm. '+2' for conservative round up.
            top_angle_side = int(round((int(top_angle_side)+2)/5.0)*5.0)
        except:
            top_angle_side = "ISA 100X65X8"
        top_angle = {20: "ISA 20X20X3", # does not satisfy min edge dist req for 12 mm bolt
                     25: "ISA 25X25X3", # does not satisfy min edge dist req for 12 mm bolt
                     30: "ISA 30X30X3", # does not satisfy min edge dist req for 12 mm bolt
                     35: "ISA 35X35X4", # does not satisfy min edge dist req for 12 mm bolt
                     40: "ISA 40X40X4",
                     45: "ISA 45X45X5",
                     50: "ISA 50X50X5",
                     55: "ISA 55X55X6",
                     60: "ISA 60X60X6",
                     65: "ISA 65X65X6",
                     70: "ISA 70X70X7",
                     75: "ISA 75X75X8",
                     80: "ISA 80X80X8",
                     90: "ISA 90X90X10",
                     "ISA 100X65X8": "ISA 100X65X8"
                     }[top_angle_side]

        return top_angle

    def sa_params(self, input_dict):
        """Intialise variables to use in calculations from input dictionary.

        Args:
            input_dict: dictionary generated based on user inputs in GUI

        Returns:
            none

        Note:
            Assumptions:
            angle f_y and f_u are equal to beam f_y and f_u respectively
            clear gap = 5 + 5 mm

        """
        # Initialise Design Preferences
        self.gamma_mb = 1.25  # partial safety factor for material - resistance of connection - bolts
        self.gamma_m0 = 1.1  # partial safety factor for material - resistance governed by yielding or buckling
        self.gamma_m1 = 1.25 # partial safety factor for material - resistance governed by ultimate stress
        self.bolt_hole_type = 1  # standard bolt hole
        # self.bolt_hole_type = 0  # oversize bolt hole
        self.custom_hole_clearance = None  # user defined hole clearance, if any
        self.beam_col_clear_gap = 5 + 5  # clearance + tolerance
        # min edge distance multiplier based on edge type (Cl 10.2.4.2)
        # self.min_edge_multiplier = 1.5  # rolled, machine-flame cut, sawn and planed edges
        self.min_edge_multiplier = 1.7  # sheared or hand flame cut edges

        self.top_angle = "ISA 100X65X8" #Initialize
        self.connectivity = input_dict['Member']['Connectivity']
        self.beam_section = input_dict['Member']['BeamSection']
        self.column_section = input_dict['Member']['ColumnSection']
        self.beam_fu = input_dict['Member']['fu (MPa)']
        self.beam_fy = input_dict['Member']['fy (MPa)']
        self.column_fy = self.beam_fy
        self.column_fu = self.beam_fu
        self.angle_fy = self.beam_fy
        self.angle_fu = self.beam_fu
        self.shear_force = input_dict['Load']['ShearForce (kN)']
        self.bolt_diameter = input_dict['Bolt']['Diameter (mm)']
        self.bolt_type = input_dict['Bolt']['Type']
        self.bolt_grade = input_dict['Bolt']['Grade']
        self.bolt_fu = int(float(self.bolt_grade)) * 100
        self.angle_sec = input_dict['Angle']["AngleSection"]

        if self.connectivity == "Beam-Beam":
            self.dict_beam_data = get_beamdata(self.beam_section)
            self.dict_column_data = get_beamdata(self.column_section)
        else:
            self.dict_beam_data = get_beamdata(self.beam_section)
            self.dict_column_data = get_columndata(self.column_section)
        self.dict_angle_data = get_angledata(self.angle_sec)

        self.beam_w_t = float(self.dict_beam_data[QString("tw")])  # beam web thickness
        self.beam_f_t = float(self.dict_beam_data[QString("T")])  # beam flange thickness
        self.beam_d = float(self.dict_beam_data[QString("D")])  # beam depth
        self.beam_w_f = float(self.dict_beam_data[QString("B")])  # beam width
        self.beam_R1 = float(self.dict_beam_data[QString("R1")])  # beam root radius
        self.column_f_t = float(self.dict_column_data[QString("T")])  # column flange thickness
        self.column_d = float(self.dict_column_data[QString("D")])  # column depth
        self.column_w_f = float(self.dict_column_data[QString("B")])  # column width
        self.column_R1 = float(self.dict_column_data[QString("R1")])  # column root radius
        self.angle_t = float(self.dict_angle_data[QString("t")])  # angle thickness
        self.angle_A = float(self.dict_angle_data[QString("A")])  # longer leg of unequal angle
        self.angle_B = float(self.dict_angle_data[QString("B")])  # shorter leg of unequal angle
        self.angle_R1 = float(self.dict_angle_data[QString("R1")])

        self.pitch = 0
        self.top_angle = self.top_angle_section()
        self.safe = True

    def print_section_properties(self):
        """Print geometric-shape properties of beam, angle and column.

        Args:
            None

        Returns:
            None

        """
        print "\nBeam section ", self.beam_section
        print self.beam_w_t, "Beam web thickness"
        print self.beam_f_t, "Beam flange thickness"
        print self.beam_d , "Beam depth"
        print self.beam_w_f, "Beam width"
        print self.beam_R1 , " Beam root radius"
        print "\nColumn section ", self.column_section
        print self.column_f_t , "Column flange thickness"
        print float(self.dict_column_data[QString("tw")]), "Column web thickness"
        print float(self.dict_column_data[QString("D")]), "Column depth"
        print float(self.dict_column_data[QString("B")]), "Column width"
        print float(self.dict_column_data[QString("R1")]), "Column root radius"
        print "\nAngle section ", self.angle_sec
        print self.angle_t , "Angle thickness"
        print self.angle_A , "Longer leg of unequal angle"
        print self.angle_B , "Shorter leg of unequal angle"
        print self.angle_R1, "Root radius of angle"

    def sa_output(self):
        """Create and return dictionary of output parameters."""
        self.output_dict = {'SeatAngle':{}, 'Bolt':{}}
        self.output_dict['SeatAngle'] = {
            "Length (mm)": self.angle_l,
            "Moment Demand (kN-mm)": self.moment_at_root_angle,
            "Moment Capacity (kN-mm)": self.moment_capacity_angle,
            "Shear Demand (kN)": self.shear_force,
            "Shear Capacity (kN)": self.outstanding_leg_shear_capacity,
            "Beam Shear Strength (kN)": self.beam_shear_strength,
            "Top Angle": self.top_angle,
            "status": self.safe
        }

        self.output_dict['Bolt'] = {
            "Shear Capacity (kN)": self.bolt_shear_capacity,
            "Bearing Capacity (kN)": self.bolt_bearing_capacity,
            "Capacity of Bolt (kN)": self.bolt_value,
            "Bolt group capacity (kN)": self.bolt_group_capacity,
            "No. of Bolts": self.bolts_provided,
            "No. of Bolts Required": self.bolts_required,
            "No. of Row": int(self.num_rows),
            "No. of Column": int(self.num_cols),
            "Pitch Distance (mm)": self.pitch,
            "Gauge Distance (mm)": self.gauge,
            "End Distance (mm)": self.min_end_dist,
            "Edge Distance (mm)": self.min_edge_dist,

            # output dictionary items for design report
            "bolt_fu": self.bolt_fu,
            "bolt_dia": self.bolt_diameter,
            "k_b": self.k_b,
            "beam_w_t": self.beam_w_t,
            "beam_fu": self.beam_fu,
            "shearforce": self.shear_force,
            "hole_dia": self.bolt_hole_diameter
        }

    def bolt_design(self, bolt_diameter):
        """Calculate bolt capacities, distances and layout.

        Args:
            None

        Returns:
            None

        """
        self.root_clearance = 5
        self.bolt_hole_diameter = bolt_diameter + self.bolt_hole_clearance(self.bolt_hole_type, bolt_diameter, self.custom_hole_clearance)

        thickness_governing_min = min(self.column_f_t.real, self.angle_t.real)
        self.calculate_distances(bolt_diameter, self.bolt_hole_diameter, self.min_edge_multiplier, thickness_governing_min)
        self.edge_dist = self.min_edge_dist
        self.end_dist = self.min_end_dist
        self.pitch = self.min_pitch

        self.calculate_kb()

        # Bolt capacity
        thickness_governing_min = min(self.column_f_t.real, self.angle_t.real)
        single_bolt = 1
        self.bolt_shear_capacity = self.bolt_shear(bolt_diameter, single_bolt, self.bolt_fu).real
        self.bolt_bearing_capacity = self.bolt_bearing(bolt_diameter, single_bolt, thickness_governing_min,
                                                  self.beam_fu, self.k_b).real
        self.bolt_value = min(self.bolt_shear_capacity, self.bolt_bearing_capacity)
        self.bolts_required = int(math.ceil(self.shear_force / self.bolt_value))
        self.bolt_group_capacity = round(self.bolts_required * self.bolt_value, 1)

    def seat_angle_connection(self, input_dict):
        """ Perform design and detailing checks based for seated angle connection.

        Args:
            input_dict (dictionary)

        Returns:
            output_dict (dictionary)

        Note:
            Algorithm:
            1) Initialise variables to use
            2) Bolt Design (layout and spacing)
            3) Determine length of outstanding leg of seated angle
            4) Determine shear strength of outstanding leg and compare with capacity

        """
        self.sa_params(input_dict)
        self.bolt_design(self.bolt_diameter)

        if self.connectivity == "Column web-Beam web":
            limiting_angle_length = self.column_d - 2*self.column_f_t - 2*self.column_R1 - self.root_clearance
            self.angle_l = int(math.ceil(min(self.beam_w_f, limiting_angle_length)))
        elif self.connectivity == "Column flange-Beam web":
            self.angle_l = int(math.ceil(min(self.beam_w_f, self.column_w_f)))

        # Determine single or double line of bolts
        length_avail = (self.angle_l - 2 * self.edge_dist)

        self.num_rows = 1
        self.num_cols = max(self.bolts_required, 2)
        self.gauge = round(int(math.ceil(length_avail / (self.num_cols - 1))),3)
        # TODO check for zero num_cols

        if self.gauge < self.min_gauge:
            self.num_rows = 2
            self.num_cols = int((self.bolts_required + 1) / 2)
            self.gauge = int(math.ceil(length_avail / (self.num_cols - 1)))
            if self.gauge < self.min_gauge:
                self.safe = False
                logger.error(": Bolt gauge is less than minimum gauge length [Cl 10.2.2]")
                logger.warning(": Bolt gauge should be more than  %2.2f mm " % (self.min_gauge))
                logger.warning(": Maximum gauge length allowed is %2.2f mm " % (self.max_spacing))
                logger.info(": Select bolt with higher grade/diameter to reduce number of bolts)")
        if self.gauge > self.max_spacing:
            """
            Assumption: keeping minimum edge distance the same and increasing the number of bolts,
                to meet the max spacing requirement.
            1) set gauge = max spacing
            2) get approx (conservative) number of bolts per line based on this gauge
            3) use the revised number of bolts per line to get revised gauge length

            The engineer can choose to use a different logic by keeping the number of bolts same,
                and increasing the edge distance.
            # gauge = max_spacing
            # edge_distance = (angle_l - (bolts_per_line-1)*gauge)/2
            """
            self.gauge = int(math.ceil(self.max_spacing))
            self.num_cols = int(math.ceil((length_avail / self.gauge) + 1))
            self.gauge = round(int(math.ceil(length_avail / (self.num_cols - 1))),3)

        self.bolts_provided = self.num_cols*self.num_rows
        self.bolt_group_capacity = round(self.bolts_provided * self.bolt_value, 1)
        self.pitch = int(math.ceil((self.num_rows-1) * (self.angle_A - self.end_dist - self.angle_t - self.angle_R1 - self.root_clearance)))
        if self.pitch < self.min_pitch and self.num_rows == 2:
            self.safe = False
            logger.error(": Bolt pitch provided is less than minimum pitch [Cl 10.2.2]")
            logger.warning(": Bolt pitch should be more than  %2.2f mm " % (self.min_pitch))
            logger.info(": Select angle with longer vertical leg OR)")
            logger.info(": Select bolt with higher grade/diameter to reduce number of bolts)")

        # length of bearing required at the root line of beam (b) = R*gamma_m0/t_w*f_yw
        # Rearranged equation from Cl 8.7.4
        bearing_length = round((self.shear_force * 1000) * self.gamma_m0 / self.beam_w_t / self.angle_fy, 3)
        # logger.info(": Length of bearing required at the root line of beam = " + str(bearing_length))

        # Required length of outstanding leg = bearing length + beam_col_clear_gap,
        outstanding_leg_length_required = bearing_length + self.beam_col_clear_gap
        # logger.info(": Outstanding leg length = " + str(outstanding_leg_length_required))

        if outstanding_leg_length_required > self.angle_B:
            self.safe = False
            logger.error(": Length of outstanding leg of angle is less than required bearing length [Cl 8.7.4]")
            logger.warning(": Outstanding leg length should be more than %2.2f mm" %(outstanding_leg_length_required))
            logger.info(": Select seated angle with longer outstanding leg")

        """ comparing 0.6*shear strength (0.6*V_d) vs shear force V for calling moment capacity routine
        Shear capacity check Cl 8.4.1
        Shear capacity of the outstanding leg of cleat = A_v * f_yw / root_3 / gamma_m0
         = w*t*fy/gamma_m0/root_3
        """
        root_3 = math.sqrt(3)
        self.outstanding_leg_shear_capacity = round(
            self.angle_l * self.angle_t * self.angle_fy * 0.001 / root_3 * self.gamma_m0, 1)  # kN
        # logger.info(": Shear strength of outstanding leg of Seated Angle = " + str(self.outstanding_leg_shear_capacity))

        if self.outstanding_leg_shear_capacity < self.shear_force:
            self.safe = False
            required_angle_thickness_shear = round(math.ceil(self.shear_force/self.outstanding_leg_shear_capacity),1)
            logger.error(": Shear capacity of outstanding leg of seated angle is insufficient [Cl 8.4.1]")
            logger.warning(": Shear capacity should be more than factored shear force %2.2f kN" %(self.shear_force))
            logger.info(": Select seated angle with thickness greater than %2.2 mm" %(required_angle_thickness_shear))

        # based on 45 degree dispersion Cl 8.7.1.3, stiff bearing length (b1) is calculated as
        # (stiff) bearing length on cleat (b1) = b - T_f (beam flange thickness) - r_b (root radius of beam flange)
        b1 = bearing_length - self.beam_f_t - self.beam_R1
        # logger.info(": Length of bearing on cleat" + str(b1))

        # Distance from the end of bearing on cleat to root angle OR A TO B = b2
        b2 = b1 + self.beam_col_clear_gap - self.angle_t - self.angle_R1
        # logger.info(": Distance A to B = " + str(b2))

        """Check moment capacity of outstanding leg

        Assumption:
            1) load is uniform over the stiff bearing length (b1)
            2) Moment (demand) is calculated at root of angle (at location B)
                due to load on the right of location B

        Shear force is compared against 0.6*shear capacity of outstanding leg to
            use appropriate moment capacity equation
        """

        self.moment_at_root_angle = round(self.shear_force * (b2 / b1) * (b2 / 2), 1)
        # logger.info(": Moment at root angle = " + str(self.moment_at_root_angle))
        # TODO moment demand negative. resolve issue. MB550 SC200 80kN 20dia3.6Bolt ISA200x150x16

        """
        Assumption
            1) beta_b (in the equation in Cl 8.2.1.2) = 1.0 as the outstanding leg is plastic section
            2) using Z_p (plastic section modulus) for moment capacity
        """
        self.leg_moment_d = (self.angle_fy /self.gamma_m0) * (self.angle_l * self.angle_t ** 2 / 6) /1000

        if self.shear_force <= 0.6 * self.outstanding_leg_shear_capacity:
            angle_moment_capacity_clause = "Cl 8.2.1.2"
            self.is_shear_high = False
            # to avoid irreversible deformation (in case of cantilever),
            # under service-ability loads, moment_d shall be less than 1.5*Z_e*f_y/gamma_m0
            leg_moment_d_limiting = 1.5 * (self.angle_fy / self.gamma_m0) * (self.angle_l * self.angle_t ** 2 / 6)  /1000
            angle_outst_leg_mcapacity = min(self.leg_moment_d, leg_moment_d_limiting)
        else:
            self.is_shear_high = True
            angle_moment_capacity_clause = "Cl 8.2.1.3"
            """ Cl 8.2.1.3
            if shear force > 0.6 * shear strength of outstanding leg:
            The moment capacity of the outstanding leg is calculated as,
            M_d = M_dv (as defined in Cl 9.2)
            Cl 9.2.2 for plastic section

            Assumption :
            M_fd=0 as the shear resiting area and moment resisting area are the same,
                for the cross section of the outstanding leg
            Thus,
            M_dv = min ((1-beta)*M_d, 1.2*Z_e*f_y/gamma_m0)
            where, beta = ((2V/V_d) - 1)^2
            """
            leg_moment_d_limiting = 1.2 * (self.angle_fy / self.gamma_m0) * (self.angle_l * self.angle_t ** 2 / 6) /1000
            beta_moment = ((2 * self.shear_force / self.outstanding_leg_shear_capacity) - 1) ** 2
            angle_outst_leg_mcapacity = min((1 - beta_moment) * self.leg_moment_d, leg_moment_d_limiting)
            self.moment_high_shear_beta = beta_moment # for design report

        self.moment_capacity_angle = round(angle_outst_leg_mcapacity, 1)
        # logger.info("Moment capacity of outstanding leg = " + str(self.moment_capacity_angle))

        if self.moment_capacity_angle < self.moment_at_root_angle:
            self.safe = False
            logger.error(": Moment capacity of outstanding leg of seated angle is not sufficient "
                         + angle_moment_capacity_clause)
            logger.warning(": Moment capacity should be at least %2.2f kN-mm" %(self.moment_at_root_angle))
            logger.info(": Increase thickness or decrease length of outstanding leg of seated angle")

        # shear capacity of beam, Vd = A_v*F_yw/root_3/gamma_m0 Cl8.4.1
        self.beam_shear_strength = round(self.beam_d * self.beam_w_t * self.beam_fy / root_3 / self.gamma_m0 / 1000, 1)
        # logger.info(": Beam shear capacity = " + str(self.beam_shear_strength))

        if self.beam_shear_strength < self.shear_force:
            self.safe = False
            logger.error(": Shear capacity of supported beam is not sufficient [Cl 8.4.1]")
            logger.warning(": Shear capacity of supported beam should be at least %2.2f kN" %(self.shear_force))
            logger.warning(": Beam design is outside the scope of this module")

        # End of calculation
        # ---------------------------------------------------------------------------
        self.sa_output()

        if self.output_dict['SeatAngle']['status'] is True:
            logger.info(": Overall seated angle connection design is safe")
            logger.debug(": =========End Of design===========")
        else:
            logger.error(": Design is not safe")
            logger.debug(": =========End Of design===========")

        return self.output_dict

# if __name__ == '__main__':
