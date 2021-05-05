import imp
import json
import os
import sys

from click.testing import CliRunner
from unittest import TestCase
from swsscommon.swsscommon import ConfigDBConnector

from .mock_tables import dbconnector

import show.main as show
from utilities_common.cli import json_dump
from utilities_common.db import Db

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, test_path)
sys.path.insert(0, modules_path)


show_queue_counters = """\
     Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
---------  -----  --------------  ---------------  -----------  ------------
Ethernet0    UC0              68               30           56            74
Ethernet0    UC1              60               43           39             1
Ethernet0    UC2              82                7           39            21
Ethernet0    UC3              52               70           19            76
Ethernet0    UC4              11               59           12            94
Ethernet0    UC5              36               62           35            40
Ethernet0    UC6              49               91            2            88
Ethernet0    UC7              33               17           94            74
Ethernet0    UC8              40               71           95            33
Ethernet0    UC9              54                8           93            78
Ethernet0   MC10              83               96           74             9
Ethernet0   MC11              15               60           61            31
Ethernet0   MC12              45               52           82            94
Ethernet0   MC13              55               88           89            52
Ethernet0   MC14              14               70           95            79
Ethernet0   MC15              68               60           66            81
Ethernet0   MC16              63                4           48            76
Ethernet0   MC17              41               73           77            74
Ethernet0   MC18              60               21           56            54
Ethernet0   MC19              57               31           12            39
Ethernet0  ALL20             N/A              N/A          N/A           N/A
Ethernet0  ALL21             N/A              N/A          N/A           N/A
Ethernet0  ALL22             N/A              N/A          N/A           N/A
Ethernet0  ALL23             N/A              N/A          N/A           N/A
Ethernet0  ALL24             N/A              N/A          N/A           N/A
Ethernet0  ALL25             N/A              N/A          N/A           N/A
Ethernet0  ALL26             N/A              N/A          N/A           N/A
Ethernet0  ALL27             N/A              N/A          N/A           N/A
Ethernet0  ALL28             N/A              N/A          N/A           N/A
Ethernet0  ALL29             N/A              N/A          N/A           N/A

     Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
---------  -----  --------------  ---------------  -----------  ------------
Ethernet4    UC0              41               96           70            98
Ethernet4    UC1              18               49           63            36
Ethernet4    UC2              99               90            3            15
Ethernet4    UC3              60               89           48            41
Ethernet4    UC4               8               84           82            94
Ethernet4    UC5              83               15           75            92
Ethernet4    UC6              84               26           50            71
Ethernet4    UC7              27               19           49            80
Ethernet4    UC8              13               89           13            33
Ethernet4    UC9              43               48           86            31
Ethernet4   MC10              50                1           57            82
Ethernet4   MC11              67               99           84            59
Ethernet4   MC12               4               58           27             5
Ethernet4   MC13              74                5           57            39
Ethernet4   MC14              21               59            4            14
Ethernet4   MC15              24               61           19            53
Ethernet4   MC16              51               15           15            32
Ethernet4   MC17              98               18           23            15
Ethernet4   MC18              41               34            9            57
Ethernet4   MC19              57                7           18            99
Ethernet4  ALL20             N/A              N/A          N/A           N/A
Ethernet4  ALL21             N/A              N/A          N/A           N/A
Ethernet4  ALL22             N/A              N/A          N/A           N/A
Ethernet4  ALL23             N/A              N/A          N/A           N/A
Ethernet4  ALL24             N/A              N/A          N/A           N/A
Ethernet4  ALL25             N/A              N/A          N/A           N/A
Ethernet4  ALL26             N/A              N/A          N/A           N/A
Ethernet4  ALL27             N/A              N/A          N/A           N/A
Ethernet4  ALL28             N/A              N/A          N/A           N/A
Ethernet4  ALL29             N/A              N/A          N/A           N/A

     Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
---------  -----  --------------  ---------------  -----------  ------------
Ethernet8    UC0              19                5           36            56
Ethernet8    UC1              38               17           68            91
Ethernet8    UC2              16               65           79            51
Ethernet8    UC3              11               97           63            72
Ethernet8    UC4              54               89           62            62
Ethernet8    UC5              13               84           30            59
Ethernet8    UC6              49               67           99            85
Ethernet8    UC7               2               63           38            88
Ethernet8    UC8               0               82           93            43
Ethernet8    UC9              80               17           91            61
Ethernet8   MC10              81               63           76            73
Ethernet8   MC11              29               16           29            66
Ethernet8   MC12              32               12           61            35
Ethernet8   MC13              79               17           72            93
Ethernet8   MC14              23               21           67            50
Ethernet8   MC15              37               10           97            14
Ethernet8   MC16              30               17           74            43
Ethernet8   MC17               0               63           54            84
Ethernet8   MC18              69               88           24            79
Ethernet8   MC19              20               12           84             3
Ethernet8  ALL20             N/A              N/A          N/A           N/A
Ethernet8  ALL21             N/A              N/A          N/A           N/A
Ethernet8  ALL22             N/A              N/A          N/A           N/A
Ethernet8  ALL23             N/A              N/A          N/A           N/A
Ethernet8  ALL24             N/A              N/A          N/A           N/A
Ethernet8  ALL25             N/A              N/A          N/A           N/A
Ethernet8  ALL26             N/A              N/A          N/A           N/A
Ethernet8  ALL27             N/A              N/A          N/A           N/A
Ethernet8  ALL28             N/A              N/A          N/A           N/A
Ethernet8  ALL29             N/A              N/A          N/A           N/A

"""


show_queue_counters_port = """\
     Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
---------  -----  --------------  ---------------  -----------  ------------
Ethernet8    UC0              19                5           36            56
Ethernet8    UC1              38               17           68            91
Ethernet8    UC2              16               65           79            51
Ethernet8    UC3              11               97           63            72
Ethernet8    UC4              54               89           62            62
Ethernet8    UC5              13               84           30            59
Ethernet8    UC6              49               67           99            85
Ethernet8    UC7               2               63           38            88
Ethernet8    UC8               0               82           93            43
Ethernet8    UC9              80               17           91            61
Ethernet8   MC10              81               63           76            73
Ethernet8   MC11              29               16           29            66
Ethernet8   MC12              32               12           61            35
Ethernet8   MC13              79               17           72            93
Ethernet8   MC14              23               21           67            50
Ethernet8   MC15              37               10           97            14
Ethernet8   MC16              30               17           74            43
Ethernet8   MC17               0               63           54            84
Ethernet8   MC18              69               88           24            79
Ethernet8   MC19              20               12           84             3
Ethernet8  ALL20             N/A              N/A          N/A           N/A
Ethernet8  ALL21             N/A              N/A          N/A           N/A
Ethernet8  ALL22             N/A              N/A          N/A           N/A
Ethernet8  ALL23             N/A              N/A          N/A           N/A
Ethernet8  ALL24             N/A              N/A          N/A           N/A
Ethernet8  ALL25             N/A              N/A          N/A           N/A
Ethernet8  ALL26             N/A              N/A          N/A           N/A
Ethernet8  ALL27             N/A              N/A          N/A           N/A
Ethernet8  ALL28             N/A              N/A          N/A           N/A
Ethernet8  ALL29             N/A              N/A          N/A           N/A

"""

show_queue_counters_json = """\
{
  "Ethernet0": {
    "ALL20": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL21": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL22": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL23": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL24": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL25": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL26": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL27": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL28": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL29": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "MC10": {
      "dropbytes": "9",
      "droppacket": "74",
      "totalbytes": "96",
      "totalpacket": "83"
    },
    "MC11": {
      "dropbytes": "31",
      "droppacket": "61",
      "totalbytes": "60",
      "totalpacket": "15"
    },
    "MC12": {
      "dropbytes": "94",
      "droppacket": "82",
      "totalbytes": "52",
      "totalpacket": "45"
    },
    "MC13": {
      "dropbytes": "52",
      "droppacket": "89",
      "totalbytes": "88",
      "totalpacket": "55"
    },
    "MC14": {
      "dropbytes": "79",
      "droppacket": "95",
      "totalbytes": "70",
      "totalpacket": "14"
    },
    "MC15": {
      "dropbytes": "81",
      "droppacket": "66",
      "totalbytes": "60",
      "totalpacket": "68"
    },
    "MC16": {
      "dropbytes": "76",
      "droppacket": "48",
      "totalbytes": "4",
      "totalpacket": "63"
    },
    "MC17": {
      "dropbytes": "74",
      "droppacket": "77",
      "totalbytes": "73",
      "totalpacket": "41"
    },
    "MC18": {
      "dropbytes": "54",
      "droppacket": "56",
      "totalbytes": "21",
      "totalpacket": "60"
    },
    "MC19": {
      "dropbytes": "39",
      "droppacket": "12",
      "totalbytes": "31",
      "totalpacket": "57"
    },
    "UC0": {
      "dropbytes": "74",
      "droppacket": "56",
      "totalbytes": "30",
      "totalpacket": "68"
    },
    "UC1": {
      "dropbytes": "1",
      "droppacket": "39",
      "totalbytes": "43",
      "totalpacket": "60"
    },
    "UC2": {
      "dropbytes": "21",
      "droppacket": "39",
      "totalbytes": "7",
      "totalpacket": "82"
    },
    "UC3": {
      "dropbytes": "76",
      "droppacket": "19",
      "totalbytes": "70",
      "totalpacket": "52"
    },
    "UC4": {
      "dropbytes": "94",
      "droppacket": "12",
      "totalbytes": "59",
      "totalpacket": "11"
    },
    "UC5": {
      "dropbytes": "40",
      "droppacket": "35",
      "totalbytes": "62",
      "totalpacket": "36"
    },
    "UC6": {
      "dropbytes": "88",
      "droppacket": "2",
      "totalbytes": "91",
      "totalpacket": "49"
    },
    "UC7": {
      "dropbytes": "74",
      "droppacket": "94",
      "totalbytes": "17",
      "totalpacket": "33"
    },
    "UC8": {
      "dropbytes": "33",
      "droppacket": "95",
      "totalbytes": "71",
      "totalpacket": "40"
    },
    "UC9": {
      "dropbytes": "78",
      "droppacket": "93",
      "totalbytes": "8",
      "totalpacket": "54"
    }
  },
  "Ethernet4": {
    "ALL20": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL21": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL22": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL23": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL24": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL25": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL26": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL27": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL28": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL29": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "MC10": {
      "dropbytes": "82",
      "droppacket": "57",
      "totalbytes": "1",
      "totalpacket": "50"
    },
    "MC11": {
      "dropbytes": "59",
      "droppacket": "84",
      "totalbytes": "99",
      "totalpacket": "67"
    },
    "MC12": {
      "dropbytes": "5",
      "droppacket": "27",
      "totalbytes": "58",
      "totalpacket": "4"
    },
    "MC13": {
      "dropbytes": "39",
      "droppacket": "57",
      "totalbytes": "5",
      "totalpacket": "74"
    },
    "MC14": {
      "dropbytes": "14",
      "droppacket": "4",
      "totalbytes": "59",
      "totalpacket": "21"
    },
    "MC15": {
      "dropbytes": "53",
      "droppacket": "19",
      "totalbytes": "61",
      "totalpacket": "24"
    },
    "MC16": {
      "dropbytes": "32",
      "droppacket": "15",
      "totalbytes": "15",
      "totalpacket": "51"
    },
    "MC17": {
      "dropbytes": "15",
      "droppacket": "23",
      "totalbytes": "18",
      "totalpacket": "98"
    },
    "MC18": {
      "dropbytes": "57",
      "droppacket": "9",
      "totalbytes": "34",
      "totalpacket": "41"
    },
    "MC19": {
      "dropbytes": "99",
      "droppacket": "18",
      "totalbytes": "7",
      "totalpacket": "57"
    },
    "UC0": {
      "dropbytes": "98",
      "droppacket": "70",
      "totalbytes": "96",
      "totalpacket": "41"
    },
    "UC1": {
      "dropbytes": "36",
      "droppacket": "63",
      "totalbytes": "49",
      "totalpacket": "18"
    },
    "UC2": {
      "dropbytes": "15",
      "droppacket": "3",
      "totalbytes": "90",
      "totalpacket": "99"
    },
    "UC3": {
      "dropbytes": "41",
      "droppacket": "48",
      "totalbytes": "89",
      "totalpacket": "60"
    },
    "UC4": {
      "dropbytes": "94",
      "droppacket": "82",
      "totalbytes": "84",
      "totalpacket": "8"
    },
    "UC5": {
      "dropbytes": "92",
      "droppacket": "75",
      "totalbytes": "15",
      "totalpacket": "83"
    },
    "UC6": {
      "dropbytes": "71",
      "droppacket": "50",
      "totalbytes": "26",
      "totalpacket": "84"
    },
    "UC7": {
      "dropbytes": "80",
      "droppacket": "49",
      "totalbytes": "19",
      "totalpacket": "27"
    },
    "UC8": {
      "dropbytes": "33",
      "droppacket": "13",
      "totalbytes": "89",
      "totalpacket": "13"
    },
    "UC9": {
      "dropbytes": "31",
      "droppacket": "86",
      "totalbytes": "48",
      "totalpacket": "43"
    }
  },
  "Ethernet8": {
    "ALL20": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL21": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL22": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL23": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL24": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL25": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL26": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL27": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL28": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL29": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "MC10": {
      "dropbytes": "73",
      "droppacket": "76",
      "totalbytes": "63",
      "totalpacket": "81"
    },
    "MC11": {
      "dropbytes": "66",
      "droppacket": "29",
      "totalbytes": "16",
      "totalpacket": "29"
    },
    "MC12": {
      "dropbytes": "35",
      "droppacket": "61",
      "totalbytes": "12",
      "totalpacket": "32"
    },
    "MC13": {
      "dropbytes": "93",
      "droppacket": "72",
      "totalbytes": "17",
      "totalpacket": "79"
    },
    "MC14": {
      "dropbytes": "50",
      "droppacket": "67",
      "totalbytes": "21",
      "totalpacket": "23"
    },
    "MC15": {
      "dropbytes": "14",
      "droppacket": "97",
      "totalbytes": "10",
      "totalpacket": "37"
    },
    "MC16": {
      "dropbytes": "43",
      "droppacket": "74",
      "totalbytes": "17",
      "totalpacket": "30"
    },
    "MC17": {
      "dropbytes": "84",
      "droppacket": "54",
      "totalbytes": "63",
      "totalpacket": "0"
    },
    "MC18": {
      "dropbytes": "79",
      "droppacket": "24",
      "totalbytes": "88",
      "totalpacket": "69"
    },
    "MC19": {
      "dropbytes": "3",
      "droppacket": "84",
      "totalbytes": "12",
      "totalpacket": "20"
    },
    "UC0": {
      "dropbytes": "56",
      "droppacket": "36",
      "totalbytes": "5",
      "totalpacket": "19"
    },
    "UC1": {
      "dropbytes": "91",
      "droppacket": "68",
      "totalbytes": "17",
      "totalpacket": "38"
    },
    "UC2": {
      "dropbytes": "51",
      "droppacket": "79",
      "totalbytes": "65",
      "totalpacket": "16"
    },
    "UC3": {
      "dropbytes": "72",
      "droppacket": "63",
      "totalbytes": "97",
      "totalpacket": "11"
    },
    "UC4": {
      "dropbytes": "62",
      "droppacket": "62",
      "totalbytes": "89",
      "totalpacket": "54"
    },
    "UC5": {
      "dropbytes": "59",
      "droppacket": "30",
      "totalbytes": "84",
      "totalpacket": "13"
    },
    "UC6": {
      "dropbytes": "85",
      "droppacket": "99",
      "totalbytes": "67",
      "totalpacket": "49"
    },
    "UC7": {
      "dropbytes": "88",
      "droppacket": "38",
      "totalbytes": "63",
      "totalpacket": "2"
    },
    "UC8": {
      "dropbytes": "43",
      "droppacket": "93",
      "totalbytes": "82",
      "totalpacket": "0"
    },
    "UC9": {
      "dropbytes": "61",
      "droppacket": "91",
      "totalbytes": "17",
      "totalpacket": "80"
    }
  }
}"""

show_queue_counters_port_json = """\
{
  "Ethernet8": {
    "ALL20": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL21": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL22": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL23": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL24": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL25": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL26": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL27": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL28": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "ALL29": {
      "dropbytes": "N/A",
      "droppacket": "N/A",
      "totalbytes": "N/A",
      "totalpacket": "N/A"
    },
    "MC10": {
      "dropbytes": "73",
      "droppacket": "76",
      "totalbytes": "63",
      "totalpacket": "81"
    },
    "MC11": {
      "dropbytes": "66",
      "droppacket": "29",
      "totalbytes": "16",
      "totalpacket": "29"
    },
    "MC12": {
      "dropbytes": "35",
      "droppacket": "61",
      "totalbytes": "12",
      "totalpacket": "32"
    },
    "MC13": {
      "dropbytes": "93",
      "droppacket": "72",
      "totalbytes": "17",
      "totalpacket": "79"
    },
    "MC14": {
      "dropbytes": "50",
      "droppacket": "67",
      "totalbytes": "21",
      "totalpacket": "23"
    },
    "MC15": {
      "dropbytes": "14",
      "droppacket": "97",
      "totalbytes": "10",
      "totalpacket": "37"
    },
    "MC16": {
      "dropbytes": "43",
      "droppacket": "74",
      "totalbytes": "17",
      "totalpacket": "30"
    },
    "MC17": {
      "dropbytes": "84",
      "droppacket": "54",
      "totalbytes": "63",
      "totalpacket": "0"
    },
    "MC18": {
      "dropbytes": "79",
      "droppacket": "24",
      "totalbytes": "88",
      "totalpacket": "69"
    },
    "MC19": {
      "dropbytes": "3",
      "droppacket": "84",
      "totalbytes": "12",
      "totalpacket": "20"
    },
    "UC0": {
      "dropbytes": "56",
      "droppacket": "36",
      "totalbytes": "5",
      "totalpacket": "19"
    },
    "UC1": {
      "dropbytes": "91",
      "droppacket": "68",
      "totalbytes": "17",
      "totalpacket": "38"
    },
    "UC2": {
      "dropbytes": "51",
      "droppacket": "79",
      "totalbytes": "65",
      "totalpacket": "16"
    },
    "UC3": {
      "dropbytes": "72",
      "droppacket": "63",
      "totalbytes": "97",
      "totalpacket": "11"
    },
    "UC4": {
      "dropbytes": "62",
      "droppacket": "62",
      "totalbytes": "89",
      "totalpacket": "54"
    },
    "UC5": {
      "dropbytes": "59",
      "droppacket": "30",
      "totalbytes": "84",
      "totalpacket": "13"
    },
    "UC6": {
      "dropbytes": "85",
      "droppacket": "99",
      "totalbytes": "67",
      "totalpacket": "49"
    },
    "UC7": {
      "dropbytes": "88",
      "droppacket": "38",
      "totalbytes": "63",
      "totalpacket": "2"
    },
    "UC8": {
      "dropbytes": "43",
      "droppacket": "93",
      "totalbytes": "82",
      "totalpacket": "0"
    },
    "UC9": {
      "dropbytes": "61",
      "droppacket": "91",
      "totalbytes": "17",
      "totalpacket": "80"
    }
  }
}"""


class TestQueue(object):
    @classmethod
    def setup_class(cls):
        os.environ["PATH"] += os.pathsep + scripts_path
        os.environ['UTILITIES_UNIT_TESTING'] = "2"
        print("SETUP")

    def test_queue_counters(self):
        runner = CliRunner()
        result = runner.invoke(
            show.cli.commands["queue"].commands["counters"],
            []
        )
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_queue_counters

    def test_queue_counters_port(self):
        runner = CliRunner()
        result = runner.invoke(
            show.cli.commands["queue"].commands["counters"],
            ["Ethernet8"]
        )
        print(result.output)
        assert result.exit_code == 0
        assert result.output == show_queue_counters_port

    def test_queue_counters_json(self):
        runner = CliRunner()
        result = runner.invoke(
            show.cli.commands["queue"].commands["counters"],
            ["--json"]
        )
        assert result.exit_code == 0
        print(result.output)
        json_output = json.loads(result.output)

        # remove "time" from the output
        for _, v in json_output.items():
            del v["time"]
        assert json_dump(json_output) == show_queue_counters_json 

    def test_queue_counters_port_json(self):
        runner = CliRunner()
        result = runner.invoke(
            show.cli.commands["queue"].commands["counters"],
            ["Ethernet8 --json"]
        )
        assert result.exit_code == 0
        print(result.output)
        json_output = json.loads(result.output)

        # remove "time" from the output
        for _, v in json_output.items():
            del v["time"]
        assert json_dump(json_output) == show_queue_counters_port_json 

    @classmethod
    def teardown_class(cls):
        os.environ["PATH"] = os.pathsep.join(os.environ["PATH"].split(os.pathsep)[:-1])
        os.environ['UTILITIES_UNIT_TESTING'] = "0"
        print("TEARDOWN")
