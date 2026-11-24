"""Domain definitions and clearly fictional demo data for VIXISU."""

FEATURES = {
    'cricket': [
        ('batting', 'Batting quality'), ('strike', 'Strike rate'),
        ('consistency', 'Consistency'), ('fielding', 'Fielding'),
        ('bowling', 'Bowling impact'), ('economy', 'Economy control'),
        ('finishing', 'Finishing'),
    ],
    'football': [
        ('passing', 'Passing'), ('vision', 'Game vision'),
        ('dribbling', 'Dribbling'), ('pace', 'Pace'),
        ('finishing', 'Finishing'), ('defending', 'Defending'),
        ('positioning', 'Positioning'),
    ],
}

ROLE_TEMPLATES = {
    'cricket': {
        'Opener': {'strike': 30, 'batting': 25, 'consistency': 20, 'fielding': 10, 'finishing': 15},
        'Middle Order': {'batting': 30, 'consistency': 30, 'strike': 15, 'fielding': 10, 'finishing': 15},
        'Finisher': {'finishing': 35, 'strike': 30, 'batting': 15, 'consistency': 10, 'fielding': 10},
        'All-Rounder': {'batting': 25, 'bowling': 25, 'fielding': 15, 'strike': 15, 'economy': 20},
        'Bowler': {'bowling': 40, 'economy': 35, 'fielding': 15, 'consistency': 10},
    },
    'football': {
        'Midfielder': {'passing': 30, 'vision': 25, 'positioning': 20, 'defending': 15, 'dribbling': 10},
        'Forward': {'finishing': 35, 'pace': 20, 'positioning': 20, 'dribbling': 15, 'vision': 10},
        'Winger': {'dribbling': 30, 'pace': 25, 'passing': 20, 'finishing': 15, 'vision': 10},
        'Defender': {'defending': 40, 'positioning': 25, 'passing': 15, 'pace': 15, 'vision': 5},
    },
}

DEMO_PLAYERS = [
    # Entirely fictional players; values are invented normalized demo skill scores, NOT actual measurements.
    ('C-01','Arjun Rao','cricket','Opener','IN',22,{'batting':88,'strike':94,'consistency':76,'fielding':67,'bowling':18,'economy':20,'finishing':82},'AR'),
    ('C-02','Kabir Mehta','cricket','Opener','IN',24,{'batting':92,'strike':81,'consistency':94,'fielding':75,'bowling':12,'economy':10,'finishing':70},'KM'),
    ('C-03','Dev Nair','cricket','Middle Order','IN',23,{'batting':87,'strike':76,'consistency':91,'fielding':78,'bowling':27,'economy':30,'finishing':83},'DN'),
    ('C-04','Rehan Malik','cricket','Finisher','IN',21,{'batting':76,'strike':97,'consistency':69,'fielding':83,'bowling':25,'economy':23,'finishing':96},'RM'),
    ('C-05','Ishan Verma','cricket','All-Rounder','IN',25,{'batting':79,'strike':84,'consistency':78,'fielding':86,'bowling':83,'economy':80,'finishing':81},'IV'),
    ('C-06','Ayaan Siddiqui','cricket','Bowler','IN',23,{'batting':22,'strike':36,'consistency':82,'fielding':79,'bowling':96,'economy':89,'finishing':25},'AS'),
    ('C-07','Nikhil Shah','cricket','Bowler','IN',26,{'batting':28,'strike':43,'consistency':88,'fielding':72,'bowling':88,'economy':95,'finishing':28},'NS'),
    ('C-08','Vihaan Das','cricket','All-Rounder','IN',22,{'batting':85,'strike':80,'consistency':81,'fielding':89,'bowling':76,'economy':72,'finishing':76},'VD'),
    ('F-01','Leo Moreno','football','Midfielder','ES',23,{'passing':95,'vision':93,'dribbling':84,'pace':74,'finishing':68,'defending':71,'positioning':90},'LM'),
    ('F-02','Noah Fischer','football','Midfielder','DE',24,{'passing':86,'vision':87,'dribbling':78,'pace':80,'finishing':70,'defending':92,'positioning':91},'NF'),
    ('F-03','Ethan Brooks','football','Forward','GB',22,{'passing':69,'vision':74,'dribbling':84,'pace':91,'finishing':96,'defending':24,'positioning':88},'EB'),
    ('F-04','Mateo Silva','football','Winger','BR',21,{'passing':81,'vision':80,'dribbling':97,'pace':96,'finishing':79,'defending':38,'positioning':77},'MS'),
    ('F-05','Amir Haddad','football','Defender','MA',25,{'passing':76,'vision':72,'dribbling':49,'pace':77,'finishing':28,'defending':96,'positioning':95},'AH'),
    ('F-06','Oliver Reed','football','Defender','GB',24,{'passing':84,'vision':80,'dribbling':61,'pace':72,'finishing':33,'defending':91,'positioning':92},'OR'),
    ('F-07','Luca Moretti','football','Forward','IT',23,{'passing':77,'vision':75,'dribbling':82,'pace':84,'finishing':89,'defending':29,'positioning':94},'LM'),
    ('F-08','Rafael Costa','football','Winger','PT',22,{'passing':89,'vision':84,'dribbling':90,'pace':88,'finishing':77,'defending':46,'positioning':82},'RC'),
]
