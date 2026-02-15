"""
TITAN V7.0 SINGULARITY - Cerberus Enhanced Engine
Advanced card intelligence: AVS verification, AI BIN scoring,
silent validation without bank flags, and target recommendations.

This module extends cerberus_core.py with:
1. AVS (Address Verification System) pre-check without live auth
2. AI-driven BIN scoring with target compatibility recommendations
3. Silent validation techniques that avoid bank fraud alerts
4. Card-to-target matching engine with success rate predictions
5. Geo-match verification (card billing vs proxy/VPN exit)
"""

import os
import hashlib
import json
import re
import secrets
import random
import math
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple
import logging

# Centralized env loading
try:
    from titan_env import load_env
    load_env()
except ImportError:
    _TITAN_ENV = Path("/opt/titan/config/titan.env")
    if _TITAN_ENV.exists():
        for _line in _TITAN_ENV.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip()
                if _v and not _v.startswith("REPLACE_WITH") and _k not in os.environ:
                    os.environ[_k] = _v

logger = logging.getLogger("TITAN-V7-CERBERUS-ENHANCED")


# ═══════════════════════════════════════════════════════════════════════════
# AVS (ADDRESS VERIFICATION SYSTEM) ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class AVSResult(Enum):
    """AVS response codes — matches real processor codes"""
    FULL_MATCH = "Y"           # Street + ZIP match
    ZIP_MATCH = "Z"            # ZIP matches, street does not
    STREET_MATCH = "A"         # Street matches, ZIP does not
    NO_MATCH = "N"             # Neither matches
    NOT_SUPPORTED = "U"        # AVS not supported by issuer
    NOT_CHECKED = "S"          # AVS not checked
    SYSTEM_ERROR = "E"         # AVS system error


@dataclass
class AVSCheckResult:
    """Result of AVS pre-verification"""
    avs_code: AVSResult
    street_match: bool
    zip_match: bool
    confidence: float           # 0.0 - 1.0
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)


class AVSEngine:
    """
    Address Verification System pre-check engine.
    
    Validates billing address components LOCALLY against known patterns
    WITHOUT making any bank API calls. This prevents:
    - Bank fraud alerts from failed AVS checks
    - Velocity flags from repeated address validation attempts
    - Cross-merchant AVS failure correlation (Forter/Riskified share this)
    
    How it works:
    1. Normalize address components (USPS format)
    2. Validate ZIP matches state
    3. Validate address format
    4. Check for known fraud patterns
    5. Score likelihood of AVS pass at target
    """
    
    # US State → ZIP prefix mapping (first 3 digits)
    STATE_ZIP_MAP = {
        'AL': ['350','351','352','354','355','356','357','358','359','360','361','362','363','364','365','366','367'],
        'AK': ['995','996','997','998','999'],
        'AZ': ['850','851','852','853','855','856','857','859','860','863','864','865'],
        'AR': ['716','717','718','719','720','721','722','723','724','725','726','727','728','729'],
        'CA': ['900','901','902','903','904','905','906','907','908','910','911','912','913','914','915','916','917','918','919','920','921','922','923','924','925','926','927','928','930','931','932','933','934','935','936','937','938','939','940','941','943','944','945','946','947','948','949','950','951','952','953','954','955','956','957','958','959','960','961'],
        'CO': ['800','801','802','803','804','805','806','807','808','809','810','811','812','813','814','815','816'],
        'CT': ['060','061','062','063','064','065','066','067','068','069'],
        'DE': ['197','198','199'],
        'FL': ['320','321','322','323','324','325','326','327','328','329','330','331','332','334','335','336','337','338','339','341','342','344','346','347','349'],
        'GA': ['300','301','302','303','304','305','306','307','308','309','310','311','312','313','314','315','316','317','318','319','398','399'],
        'HI': ['967','968'],
        'ID': ['832','833','834','835','836','837','838'],
        'IL': ['600','601','602','603','604','605','606','607','608','609','610','611','612','613','614','615','616','617','618','619','620','622','623','624','625','626','627','628','629'],
        'IN': ['460','461','462','463','464','465','466','467','468','469','470','471','472','473','474','475','476','477','478','479'],
        'IA': ['500','501','502','503','504','505','506','507','508','509','510','511','512','513','514','515','516','521','522','523','524','525','526','527','528'],
        'KS': ['660','661','662','664','665','666','667','668','669','670','671','672','673','674','675','676','677','678','679'],
        'KY': ['400','401','402','403','404','405','406','407','408','409','410','411','412','413','414','415','416','417','418','420','421','422','423','424','425','426','427'],
        'LA': ['700','701','703','704','705','706','707','708','710','711','712','713','714'],
        'ME': ['039','040','041','042','043','044','045','046','047','048','049'],
        'MD': ['206','207','208','209','210','211','212','214','215','216','217','218','219'],
        'MA': ['010','011','012','013','014','015','016','017','018','019','020','021','022','023','024','025','026','027'],
        'MI': ['480','481','482','483','484','485','486','487','488','489','490','491','492','493','494','495','496','497','498','499'],
        'MN': ['550','551','553','554','555','556','557','558','559','560','561','562','563','564','565','566','567'],
        'MS': ['386','387','388','389','390','391','392','393','394','395','396','397'],
        'MO': ['630','631','633','634','635','636','637','638','639','640','641','644','645','646','647','648','649','650','651','652','653','654','655','656','657','658'],
        'MT': ['590','591','592','593','594','595','596','597','598','599'],
        'NE': ['680','681','683','684','685','686','687','688','689','690','691','692','693'],
        'NV': ['889','890','891','893','894','895','897','898'],
        'NH': ['030','031','032','033','034','035','036','037','038'],
        'NJ': ['070','071','072','073','074','075','076','077','078','079','080','081','082','083','084','085','086','087','088','089'],
        'NM': ['870','871','873','874','875','877','878','879','880','881','882','883','884'],
        'NY': ['005','100','101','102','103','104','105','106','107','108','109','110','111','112','113','114','115','116','117','118','119','120','121','122','123','124','125','126','127','128','129','130','131','132','133','134','135','136','137','138','139','140','141','142','143','144','145','146','147','148','149'],
        'NC': ['270','271','272','273','274','275','276','277','278','279','280','281','282','283','284','285','286','287','288','289'],
        'ND': ['580','581','582','583','584','585','586','587','588'],
        'OH': ['430','431','432','433','434','435','436','437','438','439','440','441','442','443','444','445','446','447','448','449','450','451','452','453','454','455','456','457','458','459'],
        'OK': ['730','731','734','735','736','737','738','739','740','741','743','744','745','746','747','748','749'],
        'OR': ['970','971','972','973','974','975','976','977','978','979'],
        'PA': ['150','151','152','153','154','155','156','157','158','159','160','161','162','163','164','165','166','167','168','169','170','171','172','173','174','175','176','177','178','179','180','181','182','183','184','185','186','187','188','189','190','191','192','193','194','195','196'],
        'RI': ['028','029'],
        'SC': ['290','291','292','293','294','295','296','297','298','299'],
        'SD': ['570','571','572','573','574','575','576','577'],
        'TN': ['370','371','372','373','374','375','376','377','378','379','380','381','382','383','384','385'],
        'TX': ['733','750','751','752','753','754','755','756','757','758','759','760','761','762','763','764','765','766','767','768','769','770','771','772','773','774','775','776','777','778','779','780','781','782','783','784','785','786','787','788','789','790','791','792','793','794','795','796','797','798','799','885'],
        'UT': ['840','841','842','843','844','845','846','847'],
        'VT': ['050','051','052','053','054','055','056','057','058','059'],
        'VA': ['201','220','221','222','223','224','225','226','227','228','229','230','231','232','233','234','235','236','237','238','239','240','241','242','243','244','245','246'],
        'WA': ['980','981','982','983','984','985','986','988','989','990','991','992','993','994'],
        'WV': ['247','248','249','250','251','252','253','254','255','256','257','258','259','260','261','262','263','264','265','266','267','268'],
        'WI': ['530','531','532','534','535','537','538','539','540','541','542','543','544','545','546','547','548','549'],
        'WY': ['820','821','822','823','824','825','826','827','828','829','830','831'],
        'DC': ['200','202','203','204','205'],
    }
    
    # Common address abbreviation normalization
    ADDR_ABBREVIATIONS = {
        'street': 'ST', 'st': 'ST', 'str': 'ST',
        'avenue': 'AVE', 'ave': 'AVE', 'av': 'AVE',
        'boulevard': 'BLVD', 'blvd': 'BLVD',
        'drive': 'DR', 'dr': 'DR', 'drv': 'DR',
        'lane': 'LN', 'ln': 'LN',
        'road': 'RD', 'rd': 'RD',
        'court': 'CT', 'ct': 'CT',
        'place': 'PL', 'pl': 'PL',
        'circle': 'CIR', 'cir': 'CIR',
        'highway': 'HWY', 'hwy': 'HWY',
        'parkway': 'PKWY', 'pkwy': 'PKWY',
        'terrace': 'TER', 'ter': 'TER',
        'apartment': 'APT', 'apt': 'APT', '#': 'APT',
        'suite': 'STE', 'ste': 'STE',
        'unit': 'UNIT',
        'north': 'N', 'south': 'S', 'east': 'E', 'west': 'W',
        'northeast': 'NE', 'northwest': 'NW', 'southeast': 'SE', 'southwest': 'SW',
    }
    
    def normalize_address(self, address: str) -> str:
        """Normalize address to USPS standard format"""
        addr = address.upper().strip()
        # Remove extra spaces
        addr = re.sub(r'\s+', ' ', addr)
        # Remove periods
        addr = addr.replace('.', '')
        # Normalize abbreviations
        words = addr.split()
        normalized = []
        for word in words:
            lower = word.lower()
            if lower in self.ADDR_ABBREVIATIONS:
                normalized.append(self.ADDR_ABBREVIATIONS[lower])
            else:
                normalized.append(word)
        return ' '.join(normalized)
    
    def verify_zip_state(self, zip_code: str, state: str) -> bool:
        """Verify ZIP code matches state"""
        clean_zip = re.sub(r'\D', '', zip_code)
        if len(clean_zip) < 3:
            return False
        prefix = clean_zip[:3]
        state_upper = state.upper().strip()
        valid_prefixes = self.STATE_ZIP_MAP.get(state_upper, [])
        return prefix in valid_prefixes
    
    def check_avs(self, 
                  card_billing_address: str,
                  card_billing_zip: str,
                  card_billing_state: str,
                  input_address: str,
                  input_zip: str,
                  input_state: str) -> AVSCheckResult:
        """
        Pre-check AVS match likelihood WITHOUT making a bank call.
        
        Compares the cardholder's billing address against what will
        be entered at checkout. Predicts the AVS response code.
        """
        # Normalize both addresses
        norm_card_addr = self.normalize_address(card_billing_address)
        norm_input_addr = self.normalize_address(input_address)
        
        # Clean ZIPs
        card_zip = re.sub(r'\D', '', card_billing_zip)[:5]
        input_zip_clean = re.sub(r'\D', '', input_zip)[:5]
        
        # Check ZIP match
        zip_match = card_zip == input_zip_clean
        
        # Check street match (extract street number + name)
        card_street_num = re.match(r'^(\d+)', norm_card_addr)
        input_street_num = re.match(r'^(\d+)', norm_input_addr)
        
        street_num_match = False
        if card_street_num and input_street_num:
            street_num_match = card_street_num.group(1) == input_street_num.group(1)
        
        # Fuzzy street name comparison
        card_words = set(norm_card_addr.split())
        input_words = set(norm_input_addr.split())
        common_words = card_words & input_words
        
        # Remove common abbreviations from comparison
        noise_words = {'APT', 'STE', 'UNIT', '#', 'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW'}
        meaningful_card = card_words - noise_words
        meaningful_input = input_words - noise_words
        meaningful_common = meaningful_card & meaningful_input
        
        street_similarity = len(meaningful_common) / max(len(meaningful_card), 1)
        street_match = street_num_match and street_similarity >= 0.5
        
        # State match
        state_match = card_billing_state.upper().strip() == input_state.upper().strip()
        
        # Determine AVS code
        if street_match and zip_match:
            avs_code = AVSResult.FULL_MATCH
            confidence = 0.95
            recommendation = "AVS will pass — full address + ZIP match. Safe to proceed."
        elif zip_match and not street_match:
            avs_code = AVSResult.ZIP_MATCH
            confidence = 0.70
            recommendation = "ZIP matches but street differs. Most merchants accept ZIP-only match. Medium risk."
        elif street_match and not zip_match:
            avs_code = AVSResult.STREET_MATCH
            confidence = 0.50
            recommendation = "Street matches but ZIP differs. Check for typo in ZIP code. Higher decline risk."
        else:
            avs_code = AVSResult.NO_MATCH
            confidence = 0.10
            recommendation = "CRITICAL: Neither street nor ZIP match. AVS will fail. Verify billing address via OSINT."
        
        if not state_match:
            confidence *= 0.5
            recommendation += " WARNING: State mismatch detected."
        
        # ZIP-state validation
        if not self.verify_zip_state(input_zip_clean, input_state):
            confidence *= 0.3
            recommendation += " CRITICAL: ZIP code does not match state — instant decline."
        
        return AVSCheckResult(
            avs_code=avs_code,
            street_match=street_match,
            zip_match=zip_match,
            confidence=confidence,
            recommendation=recommendation,
            details={
                "normalized_card_address": norm_card_addr,
                "normalized_input_address": norm_input_addr,
                "state_match": state_match,
                "zip_state_valid": self.verify_zip_state(input_zip_clean, input_state),
                "street_similarity": round(street_similarity, 2),
            }
        )


# ═══════════════════════════════════════════════════════════════════════════
# AI BIN SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BINScore:
    """AI-generated BIN intelligence score"""
    bin_number: str
    overall_score: float        # 0-100 (higher = better for use)
    bank: str
    country: str
    card_type: str              # credit, debit, prepaid
    card_level: str             # classic, gold, platinum, etc.
    network: str                # visa, mastercard, amex
    risk_factors: List[str]
    recommendations: List[str]
    target_compatibility: Dict[str, float]  # target -> compatibility score
    estimated_3ds_rate: float
    estimated_success_rate: float
    avs_strictness: str         # relaxed, moderate, strict
    velocity_limit_daily: int   # estimated daily transaction limit
    max_single_amount: float


class BINScoringEngine:
    """
    AI-driven BIN scoring engine that evaluates card BINs for:
    - Target compatibility (which merchants will accept this BIN)
    - Success rate prediction
    - Risk factor analysis
    - Spending limit estimation
    - 3DS trigger probability
    - AVS strictness by issuer
    
    All scoring is done LOCALLY — no API calls, no bank alerts.
    """
    
    # Bank AVS strictness profiles
    BANK_AVS_PROFILES = {
        'Chase': {'strictness': 'strict', 'requires_zip': True, 'requires_street': True, 'allows_zip_only': False},
        'Bank of America': {'strictness': 'strict', 'requires_zip': True, 'requires_street': True, 'allows_zip_only': True},
        'Capital One': {'strictness': 'moderate', 'requires_zip': True, 'requires_street': False, 'allows_zip_only': True},
        'Citi': {'strictness': 'moderate', 'requires_zip': True, 'requires_street': False, 'allows_zip_only': True},
        'Wells Fargo': {'strictness': 'strict', 'requires_zip': True, 'requires_street': True, 'allows_zip_only': False},
        'US Bank': {'strictness': 'moderate', 'requires_zip': True, 'requires_street': False, 'allows_zip_only': True},
        'USAA': {'strictness': 'relaxed', 'requires_zip': True, 'requires_street': False, 'allows_zip_only': True},
        'Navy Federal': {'strictness': 'relaxed', 'requires_zip': True, 'requires_street': False, 'allows_zip_only': True},
        'American Express': {'strictness': 'strict', 'requires_zip': True, 'requires_street': True, 'allows_zip_only': False},
        'Discover': {'strictness': 'moderate', 'requires_zip': True, 'requires_street': False, 'allows_zip_only': True},
        'Barclays': {'strictness': 'moderate', 'requires_zip': True, 'requires_street': False, 'allows_zip_only': True},
        'Monzo': {'strictness': 'relaxed', 'requires_zip': False, 'requires_street': False, 'allows_zip_only': True},
        'Revolut': {'strictness': 'relaxed', 'requires_zip': False, 'requires_street': False, 'allows_zip_only': True},
    }
    
    # Card level spending profiles
    LEVEL_PROFILES = {
        'centurion': {'max_single': 50000, 'daily_limit': 100000, 'base_score': 95, '3ds_rate': 0.15},
        'platinum': {'max_single': 15000, 'daily_limit': 30000, 'base_score': 90, '3ds_rate': 0.20},
        'signature': {'max_single': 10000, 'daily_limit': 20000, 'base_score': 85, '3ds_rate': 0.25},
        'world_elite': {'max_single': 15000, 'daily_limit': 25000, 'base_score': 88, '3ds_rate': 0.22},
        'world': {'max_single': 5000, 'daily_limit': 10000, 'base_score': 80, '3ds_rate': 0.30},
        'gold': {'max_single': 5000, 'daily_limit': 10000, 'base_score': 78, '3ds_rate': 0.30},
        'classic': {'max_single': 2000, 'daily_limit': 5000, 'base_score': 65, '3ds_rate': 0.35},
        'standard': {'max_single': 1500, 'daily_limit': 3000, 'base_score': 60, '3ds_rate': 0.40},
    }
    
    # Target compatibility matrix
    TARGET_COMPATIBILITY = {
        'eneba.com': {
            'best_levels': ['gold', 'platinum', 'signature', 'world', 'classic'],
            'best_types': ['credit'],
            'best_countries': ['US', 'CA', 'GB', 'AU'],
            'avs_requirement': 'zip_only',
            'max_amount': 500,
            'base_compat': 0.85,
        },
        'g2a.com': {
            'best_levels': ['gold', 'platinum', 'world', 'classic'],
            'best_types': ['credit', 'debit'],
            'best_countries': ['US', 'CA', 'GB', 'DE', 'NL'],
            'avs_requirement': 'zip_only',
            'max_amount': 300,
            'base_compat': 0.80,
        },
        'amazon.com': {
            'best_levels': ['platinum', 'signature', 'world_elite', 'gold'],
            'best_types': ['credit'],
            'best_countries': ['US'],
            'avs_requirement': 'full',
            'max_amount': 2000,
            'base_compat': 0.70,
        },
        'steam': {
            'best_levels': ['classic', 'gold', 'platinum'],
            'best_types': ['credit', 'debit'],
            'best_countries': ['US', 'CA', 'GB', 'AU', 'DE'],
            'avs_requirement': 'zip_only',
            'max_amount': 500,
            'base_compat': 0.82,
        },
        'bestbuy.com': {
            'best_levels': ['platinum', 'signature', 'world_elite'],
            'best_types': ['credit'],
            'best_countries': ['US'],
            'avs_requirement': 'full',
            'max_amount': 3000,
            'base_compat': 0.55,
        },
        'walmart.com': {
            'best_levels': ['classic', 'gold', 'platinum', 'signature'],
            'best_types': ['credit', 'debit'],
            'best_countries': ['US'],
            'avs_requirement': 'zip_only',
            'max_amount': 1000,
            'base_compat': 0.75,
        },
        'priceline.com': {
            'best_levels': ['platinum', 'signature', 'world_elite', 'gold'],
            'best_types': ['credit'],
            'best_countries': ['US', 'CA'],
            'avs_requirement': 'full',
            'max_amount': 5000,
            'base_compat': 0.60,
        },
    }
    
    # Known high-risk BIN prefixes (virtual, prepaid, high-fraud)
    HIGH_RISK_BINS = {
        '414720', '424631', '428837', '431274', '438857',
        '453245', '476173', '485932', '486208', '489019',
        '511563', '517805', '524897', '530136', '531993',
        '540443', '542418', '548760', '552289', '558848',
        '604646', '627571', '636297', '639463',
    }
    
    # Extended BIN database
    BIN_DATABASE = {
        '401200': {'bank': 'Chase', 'country': 'US', 'type': 'credit', 'level': 'signature', 'network': 'visa'},
        '414720': {'bank': 'Chase', 'country': 'US', 'type': 'debit', 'level': 'classic', 'network': 'visa'},
        '421783': {'bank': 'Bank of America', 'country': 'US', 'type': 'credit', 'level': 'platinum', 'network': 'visa'},
        '426684': {'bank': 'Capital One', 'country': 'US', 'type': 'credit', 'level': 'platinum', 'network': 'visa'},
        '428485': {'bank': 'Citi', 'country': 'US', 'type': 'credit', 'level': 'signature', 'network': 'visa'},
        '433610': {'bank': 'Wells Fargo', 'country': 'US', 'type': 'credit', 'level': 'signature', 'network': 'visa'},
        '440066': {'bank': 'US Bank', 'country': 'US', 'type': 'credit', 'level': 'platinum', 'network': 'visa'},
        '453245': {'bank': 'USAA', 'country': 'US', 'type': 'credit', 'level': 'signature', 'network': 'visa'},
        '459500': {'bank': 'Navy Federal', 'country': 'US', 'type': 'credit', 'level': 'signature', 'network': 'visa'},
        '512345': {'bank': 'Chase', 'country': 'US', 'type': 'credit', 'level': 'world', 'network': 'mastercard'},
        '517805': {'bank': 'Bank of America', 'country': 'US', 'type': 'credit', 'level': 'world', 'network': 'mastercard'},
        '524897': {'bank': 'Capital One', 'country': 'US', 'type': 'credit', 'level': 'world_elite', 'network': 'mastercard'},
        '530136': {'bank': 'Citi', 'country': 'US', 'type': 'credit', 'level': 'world', 'network': 'mastercard'},
        '540443': {'bank': 'Wells Fargo', 'country': 'US', 'type': 'credit', 'level': 'world', 'network': 'mastercard'},
        '548760': {'bank': 'US Bank', 'country': 'US', 'type': 'credit', 'level': 'world', 'network': 'mastercard'},
        '552289': {'bank': 'Barclays', 'country': 'US', 'type': 'credit', 'level': 'world', 'network': 'mastercard'},
        '378282': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'gold', 'network': 'amex'},
        '371449': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'platinum', 'network': 'amex'},
        '374245': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'centurion', 'network': 'amex'},
        '376411': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'gold', 'network': 'amex'},
        '454313': {'bank': 'Barclays', 'country': 'GB', 'type': 'debit', 'level': 'classic', 'network': 'visa'},
        '492181': {'bank': 'Monzo', 'country': 'GB', 'type': 'debit', 'level': 'classic', 'network': 'visa'},
        '535522': {'bank': 'Revolut', 'country': 'GB', 'type': 'debit', 'level': 'standard', 'network': 'mastercard'},
        '400360': {'bank': 'Visa Inc.', 'country': 'US', 'type': 'credit', 'level': 'classic', 'network': 'visa'},
        '403587': {'bank': 'Chase', 'country': 'US', 'type': 'credit', 'level': 'classic', 'network': 'visa'},
        '556737': {'bank': 'Fifth Third', 'country': 'US', 'type': 'credit', 'level': 'world', 'network': 'mastercard'},
    }
    
    def score_bin(self, bin_number: str, target: Optional[str] = None) -> BINScore:
        """
        Generate comprehensive BIN intelligence score.
        
        All analysis is LOCAL — zero API calls, zero bank alerts.
        """
        bin6 = bin_number[:6]
        bin_info = self.BIN_DATABASE.get(bin6, self._infer_bin(bin6))
        
        bank = bin_info.get('bank', 'Unknown')
        country = bin_info.get('country', 'US')
        card_type = bin_info.get('type', 'credit')
        level = bin_info.get('level', 'classic')
        network = bin_info.get('network', 'visa')
        
        level_profile = self.LEVEL_PROFILES.get(level, self.LEVEL_PROFILES['classic'])
        bank_avs = self.BANK_AVS_PROFILES.get(bank, {'strictness': 'moderate'})
        
        # Calculate overall score
        base_score = level_profile['base_score']
        risk_factors = []
        recommendations = []
        
        # Adjust for card type
        if card_type == 'debit':
            base_score -= 10
            risk_factors.append("Debit card — lower limits, higher decline rate")
            recommendations.append("Prefer credit cards over debit for higher success")
        elif card_type == 'prepaid':
            base_score -= 30
            risk_factors.append("PREPAID card — very high decline rate on most merchants")
            recommendations.append("Avoid prepaid for e-commerce — use only for digital/crypto")
        
        # Adjust for high-risk BIN
        if bin6 in self.HIGH_RISK_BINS:
            base_score -= 25
            risk_factors.append("BIN is on high-risk/virtual card list")
            recommendations.append("This BIN may trigger extra scrutiny — use with low-value targets only")
        
        # Adjust for country
        if country not in ('US', 'CA', 'GB', 'AU'):
            base_score -= 15
            risk_factors.append(f"Non-tier-1 country ({country}) — higher cross-border decline rate")
            recommendations.append("Match proxy/VPN exit to card's billing country")
        
        # Adjust for AVS strictness
        if bank_avs.get('strictness') == 'strict':
            base_score -= 5
            risk_factors.append(f"{bank} has strict AVS — must match street + ZIP exactly")
            recommendations.append("Verify billing address via OSINT before checkout")
        
        # Target compatibility
        target_compat = {}
        for tgt, profile in self.TARGET_COMPATIBILITY.items():
            compat = profile['base_compat']
            
            if level in profile['best_levels']:
                compat += 0.10
            if card_type in profile['best_types']:
                compat += 0.05
            if country in profile['best_countries']:
                compat += 0.05
            else:
                compat -= 0.20
            
            if bin6 in self.HIGH_RISK_BINS:
                compat -= 0.25
            
            target_compat[tgt] = round(min(compat, 0.99), 2)
        
        # Success rate estimation
        success_rate = base_score / 100.0
        if card_type == 'credit' and level in ('platinum', 'signature', 'world_elite', 'centurion'):
            success_rate = min(success_rate + 0.05, 0.98)
        
        # Recommendations
        if base_score >= 80:
            recommendations.insert(0, f"HIGH QUALITY BIN — {bank} {level.replace('_', ' ').title()} {network.upper()}")
        elif base_score >= 60:
            recommendations.insert(0, f"MEDIUM QUALITY — suitable for moderate-value targets")
        else:
            recommendations.insert(0, f"LOW QUALITY — use only for low-value digital goods")
        
        # Best targets
        sorted_targets = sorted(target_compat.items(), key=lambda x: x[1], reverse=True)
        best = [t for t, s in sorted_targets[:3]]
        recommendations.append(f"Best targets: {', '.join(best)}")
        
        overall = max(0, min(100, base_score))
        
        return BINScore(
            bin_number=bin6,
            overall_score=overall,
            bank=bank,
            country=country,
            card_type=card_type,
            card_level=level,
            network=network,
            risk_factors=risk_factors,
            recommendations=recommendations,
            target_compatibility=target_compat,
            estimated_3ds_rate=level_profile['3ds_rate'],
            estimated_success_rate=round(success_rate, 2),
            avs_strictness=bank_avs.get('strictness', 'moderate'),
            velocity_limit_daily=level_profile['daily_limit'],
            max_single_amount=level_profile['max_single'],
        )
    
    def _infer_bin(self, bin6: str) -> Dict[str, str]:
        """Infer BIN info from number pattern when not in database"""
        network = 'visa'
        if bin6.startswith('4'):
            network = 'visa'
        elif bin6[:2] in ('51', '52', '53', '54', '55') or bin6[:2] in ('22', '23', '24', '25', '26', '27'):
            network = 'mastercard'
        elif bin6[:2] in ('34', '37'):
            network = 'amex'
        elif bin6.startswith('6'):
            network = 'discover'
        
        return {
            'bank': 'Unknown',
            'country': 'US',
            'type': 'credit',
            'level': 'classic',
            'network': network,
        }
    
    def get_target_recommendation(self, bin_number: str, amount: float) -> Dict[str, Any]:
        """Get specific target recommendation for a BIN + amount combination"""
        score = self.score_bin(bin_number)
        
        viable_targets = []
        for target, compat in score.target_compatibility.items():
            profile = self.TARGET_COMPATIBILITY.get(target, {})
            max_amt = profile.get('max_amount', 1000)
            
            if amount <= max_amt and compat >= 0.50:
                viable_targets.append({
                    'target': target,
                    'compatibility': compat,
                    'max_amount': max_amt,
                    'avs_requirement': profile.get('avs_requirement', 'full'),
                    'recommendation': 'RECOMMENDED' if compat >= 0.75 else 'POSSIBLE' if compat >= 0.60 else 'RISKY',
                })
        
        viable_targets.sort(key=lambda x: x['compatibility'], reverse=True)
        
        return {
            'bin_score': score,
            'amount': amount,
            'viable_targets': viable_targets,
            'best_target': viable_targets[0] if viable_targets else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# SILENT VALIDATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class SilentValidationEngine:
    """
    Silent card validation techniques that avoid triggering bank alerts.
    
    Standard Stripe SetupIntent validation can trigger:
    - Push notification: "Did you authorize this?"
    - SMS alert: "Unusual activity on your card"
    - Email: "Transaction attempt from new merchant"
    
    This engine provides alternative validation methods:
    1. BIN-only validation (zero bank contact)
    2. Tokenization-only check (creates token, doesn't auth)
    3. $0 authorization (some processors support)
    4. Timing-aware validation (during bank processing windows)
    """
    
    # Banks with aggressive push notifications
    ALERT_AGGRESSIVE_BANKS = {
        'Chase', 'Bank of America', 'Wells Fargo', 'Capital One',
        'Citi', 'USAA', 'Navy Federal',
    }
    
    # Banks with relaxed notification
    ALERT_RELAXED_BANKS = {
        'Barclays', 'Monzo', 'Revolut', 'Discover',
    }
    
    # Optimal validation time windows (UTC) — bank processing is lighter
    QUIET_WINDOWS = [
        (2, 5),    # 2AM-5AM — batch processing, fewer alerts
        (12, 14),  # 12PM-2PM — lunch hour, alert fatigue
    ]
    
    def get_validation_strategy(self, bin_number: str, bank: str) -> Dict[str, Any]:
        """
        Determine the safest validation strategy for a given card.
        Returns strategy that minimizes chance of cardholder notification.
        """
        is_aggressive = bank in self.ALERT_AGGRESSIVE_BANKS
        is_relaxed = bank in self.ALERT_RELAXED_BANKS
        
        # Current hour (UTC)
        current_hour = datetime.utcnow().hour
        in_quiet_window = any(start <= current_hour < end for start, end in self.QUIET_WINDOWS)
        
        strategies = []
        
        # Strategy 1: BIN-only (safest — zero bank contact)
        strategies.append({
            'method': 'bin_only',
            'safety_score': 100,
            'accuracy': 50,
            'description': 'BIN database lookup only. No bank contact. Cannot confirm card is live.',
            'triggers_alert': False,
            'when_to_use': 'Always safe. Use as first pass.',
        })
        
        # Strategy 2: Tokenization only
        strategies.append({
            'method': 'tokenize_only',
            'safety_score': 85 if is_relaxed else 70 if not is_aggressive else 55,
            'accuracy': 75,
            'description': 'Create payment token without authorization. Some banks may send push notification.',
            'triggers_alert': is_aggressive,
            'when_to_use': 'Use for relaxed banks or during quiet windows.',
        })
        
        # Strategy 3: $0 auth
        strategies.append({
            'method': 'zero_auth',
            'safety_score': 60 if is_relaxed else 40 if not is_aggressive else 20,
            'accuracy': 95,
            'description': '$0 authorization check. Most accurate but may trigger "new merchant" alert.',
            'triggers_alert': True,
            'when_to_use': 'Use only for relaxed banks during quiet windows.',
        })
        
        # Strategy 4: SetupIntent (standard Cerberus)
        strategies.append({
            'method': 'setup_intent',
            'safety_score': 50 if is_relaxed else 30 if not is_aggressive else 15,
            'accuracy': 98,
            'description': 'Full SetupIntent validation. High accuracy but likely triggers push notification.',
            'triggers_alert': True,
            'when_to_use': 'Last resort. Use only if other methods inconclusive.',
        })
        
        # Select recommended strategy
        if is_aggressive:
            recommended = 'bin_only'
            rationale = f"{bank} sends aggressive push notifications. BIN-only validation recommended to avoid alerting cardholder."
        elif is_relaxed and in_quiet_window:
            recommended = 'tokenize_only'
            rationale = f"{bank} has relaxed notifications and we're in a quiet processing window. Tokenization is safe."
        elif in_quiet_window:
            recommended = 'tokenize_only'
            rationale = f"Currently in quiet processing window ({current_hour}:00 UTC). Tokenization carries lower risk."
        else:
            recommended = 'bin_only'
            rationale = f"Outside quiet window and {bank} may send alerts. BIN-only is safest."
        
        return {
            'recommended_strategy': recommended,
            'rationale': rationale,
            'bank': bank,
            'is_aggressive_bank': is_aggressive,
            'in_quiet_window': in_quiet_window,
            'current_hour_utc': current_hour,
            'strategies': strategies,
            'psp_credentials_configured': self._get_configured_psps(),
        }
    
    def _get_configured_psps(self) -> Dict[str, bool]:
        """Check which PSP credentials are configured in titan.env."""
        return {
            'stripe': bool(os.getenv('TITAN_STRIPE_SECRET_KEY', '')),
            'paypal': bool(os.getenv('TITAN_PAYPAL_CLIENT_ID', '')),
            'braintree': bool(os.getenv('TITAN_BRAINTREE_MERCHANT_ID', '')),
        }
    
    def execute_validation(self, card_number: str, exp_month: int, exp_year: int,
                           cvc: str, strategy: str = 'auto',
                           bank: str = 'Unknown') -> Dict[str, Any]:
        """
        Execute silent validation using the recommended strategy.
        Requires PSP credentials in titan.env.
        
        Returns result dict with: success, method_used, live, error
        """
        if strategy == 'auto':
            rec = self.get_validation_strategy(card_number[:6], bank)
            strategy = rec['recommended_strategy']
        
        if strategy == 'bin_only':
            return {
                'success': True, 'method_used': 'bin_only', 'live': None,
                'note': 'BIN-only check — card liveness not confirmed',
            }
        
        # Attempt Stripe $0 auth or tokenize
        stripe_key = os.getenv('TITAN_STRIPE_SECRET_KEY', '')
        if stripe_key:
            return self._stripe_validate(stripe_key, card_number, exp_month, exp_year, cvc, strategy)
        
        # Attempt PayPal tokenize
        pp_client = os.getenv('TITAN_PAYPAL_CLIENT_ID', '')
        pp_secret = os.getenv('TITAN_PAYPAL_SECRET', '')
        if pp_client and pp_secret:
            return self._paypal_validate(pp_client, pp_secret, strategy)
        
        return {
            'success': False, 'method_used': 'none', 'live': None,
            'error': 'No PSP credentials configured. Edit /opt/titan/config/titan.env',
        }
    
    def _stripe_validate(self, api_key: str, card_number: str,
                         exp_month: int, exp_year: int, cvc: str,
                         strategy: str) -> Dict[str, Any]:
        """Execute Stripe-based validation."""
        try:
            import stripe
            stripe.api_key = api_key
            
            if strategy in ('tokenize_only', 'tokenize'):
                token = stripe.Token.create(card={
                    'number': card_number,
                    'exp_month': exp_month,
                    'exp_year': exp_year,
                    'cvc': cvc,
                })
                return {
                    'success': True, 'method_used': 'stripe_tokenize',
                    'live': True, 'token_id': token.id,
                    'card_brand': token.card.brand,
                    'last4': token.card.last4,
                }
            elif strategy in ('zero_auth', 'setup_intent'):
                pm = stripe.PaymentMethod.create(
                    type='card',
                    card={
                        'number': card_number,
                        'exp_month': exp_month,
                        'exp_year': exp_year,
                        'cvc': cvc,
                    },
                )
                si = stripe.SetupIntent.create(
                    payment_method=pm.id,
                    confirm=True,
                    usage='off_session',
                )
                return {
                    'success': True, 'method_used': f'stripe_{strategy}',
                    'live': si.status == 'succeeded',
                    'status': si.status,
                    'payment_method': pm.id,
                }
            else:
                return {'success': False, 'error': f'Unknown strategy: {strategy}'}
        except ImportError:
            return {'success': False, 'error': 'stripe package not installed. pip install stripe'}
        except Exception as e:
            return {'success': False, 'method_used': f'stripe_{strategy}', 'live': False, 'error': str(e)}
    
    def _paypal_validate(self, client_id: str, secret: str,
                         strategy: str) -> Dict[str, Any]:
        """Execute PayPal-based validation (order token only)."""
        try:
            import httpx
            mode = os.getenv('TITAN_PAYPAL_MODE', 'live')
            base = 'https://api-m.paypal.com' if mode == 'live' else 'https://api-m.sandbox.paypal.com'
            
            auth_resp = httpx.post(
                f'{base}/v1/oauth2/token',
                data={'grant_type': 'client_credentials'},
                auth=(client_id, secret),
                timeout=10,
            )
            if auth_resp.status_code != 200:
                return {'success': False, 'error': f'PayPal auth failed: {auth_resp.status_code}'}
            
            token = auth_resp.json().get('access_token', '')
            return {
                'success': True, 'method_used': 'paypal_token',
                'live': None,
                'note': 'PayPal OAuth token obtained. Use Orders API for further validation.',
                'access_token_prefix': token[:12] + '...' if token else '',
            }
        except ImportError:
            return {'success': False, 'error': 'httpx package not installed. pip install httpx'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# GEO MATCH CHECKER
# ═══════════════════════════════════════════════════════════════════════════

class GeoMatchChecker:
    """
    Verifies geographic consistency between card billing address,
    proxy/VPN exit IP, and browser timezone/locale.
    
    Mismatches trigger immediate review at Forter, Riskified, SEON.
    """
    
    # State → timezone mapping
    STATE_TIMEZONES = {
        'CT': 'America/New_York', 'ME': 'America/New_York', 'MA': 'America/New_York',
        'NH': 'America/New_York', 'RI': 'America/New_York', 'VT': 'America/New_York',
        'NJ': 'America/New_York', 'NY': 'America/New_York', 'PA': 'America/New_York',
        'DE': 'America/New_York', 'MD': 'America/New_York', 'VA': 'America/New_York',
        'WV': 'America/New_York', 'NC': 'America/New_York', 'SC': 'America/New_York',
        'GA': 'America/New_York', 'FL': 'America/New_York', 'DC': 'America/New_York',
        'OH': 'America/New_York', 'MI': 'America/New_York', 'IN': 'America/Indiana/Indianapolis',
        'AL': 'America/Chicago', 'IL': 'America/Chicago', 'IA': 'America/Chicago',
        'KS': 'America/Chicago', 'KY': 'America/New_York', 'LA': 'America/Chicago',
        'MN': 'America/Chicago', 'MS': 'America/Chicago', 'MO': 'America/Chicago',
        'NE': 'America/Chicago', 'ND': 'America/Chicago', 'OK': 'America/Chicago',
        'SD': 'America/Chicago', 'TN': 'America/Chicago', 'TX': 'America/Chicago',
        'WI': 'America/Chicago', 'AR': 'America/Chicago',
        'AZ': 'America/Phoenix', 'CO': 'America/Denver', 'ID': 'America/Boise',
        'MT': 'America/Denver', 'NM': 'America/Denver', 'UT': 'America/Denver',
        'WY': 'America/Denver',
        'CA': 'America/Los_Angeles', 'NV': 'America/Los_Angeles',
        'OR': 'America/Los_Angeles', 'WA': 'America/Los_Angeles',
        'AK': 'America/Anchorage', 'HI': 'Pacific/Honolulu',
    }
    
    def check_geo_consistency(self, billing_state: str, exit_ip_state: Optional[str],
                               browser_timezone: str) -> Dict[str, Any]:
        """Check geographic consistency across all signals"""
        expected_tz = self.STATE_TIMEZONES.get(billing_state.upper(), 'America/New_York')
        
        tz_match = browser_timezone == expected_tz
        ip_match = exit_ip_state is None or exit_ip_state.upper() == billing_state.upper()
        
        issues = []
        if not tz_match:
            issues.append(f"Timezone mismatch: browser={browser_timezone}, expected={expected_tz}")
        if not ip_match:
            issues.append(f"IP geo mismatch: exit={exit_ip_state}, billing={billing_state}")
        
        score = 1.0
        if not tz_match:
            score -= 0.4
        if not ip_match:
            score -= 0.4
        
        return {
            'consistent': len(issues) == 0,
            'score': max(0, score),
            'billing_state': billing_state,
            'expected_timezone': expected_tz,
            'actual_timezone': browser_timezone,
            'ip_state': exit_ip_state,
            'timezone_match': tz_match,
            'ip_match': ip_match,
            'issues': issues,
            'recommendation': 'All geo signals consistent' if not issues else 'FIX: ' + '; '.join(issues),
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.0 HARDENING: OSINT VERIFICATION FRAMEWORK
# Research §6.2: 'The module integrates with OSINT tools like
# TruePeopleSearch, FastPeopleSearch, and Whitepages.'
# ═══════════════════════════════════════════════════════════════════════════

class OSINTVerificationResult(Enum):
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    MISMATCH = "mismatch"


@dataclass
class OSINTReport:
    """OSINT verification report for a cardholder"""
    person_exists: bool
    address_match: bool
    phone_valid: bool
    address_type: str                # residential, commercial, po_box, mail_drop
    confidence_score: float          # 0.0 - 1.0
    result: OSINTVerificationResult
    sources_checked: List[str]
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""


class OSINTVerifier:
    """
    OSINT verification framework for cardholder identity.
    
    Research: 'The system verifies:
    1. Does the person exist?
    2. Is the address associated with their name?
    3. Is the phone number valid and consistent with the location?
    4. Is the address residential (higher trust) or commercial (lower trust)?'
    
    This module provides the FRAMEWORK and CHECKLIST for OSINT verification.
    Actual queries are executed by the operator using the listed tools.
    Automated scraping of these services would violate their ToS.
    """
    
    # OSINT data sources with query templates
    OSINT_SOURCES = {
        'truepeoplesearch': {
            'name': 'TruePeopleSearch',
            'url': 'https://www.truepeoplesearch.com/find/person',
            'query_format': 'Search: "{name}" in "{city}, {state}"',
            'checks': ['person_exists', 'address_match', 'phone_match'],
            'reliability': 0.85,
        },
        'fastpeoplesearch': {
            'name': 'FastPeopleSearch',
            'url': 'https://www.fastpeoplesearch.com',
            'query_format': 'Search: "{name}" at "{address}, {city}, {state}"',
            'checks': ['person_exists', 'address_match', 'relatives'],
            'reliability': 0.80,
        },
        'whitepages': {
            'name': 'Whitepages',
            'url': 'https://www.whitepages.com/name',
            'query_format': 'Search: "{name}" in "{city}, {state} {zip}"',
            'checks': ['person_exists', 'address_match', 'phone_match', 'address_type'],
            'reliability': 0.90,
        },
        'spokeo': {
            'name': 'Spokeo',
            'url': 'https://www.spokeo.com',
            'query_format': 'Search: "{name}" or reverse phone "{phone}"',
            'checks': ['person_exists', 'address_match', 'email_match'],
            'reliability': 0.75,
        },
    }
    
    # Address type classification
    ADDRESS_TYPE_INDICATORS = {
        'residential': {
            'keywords': ['house', 'apartment', 'condo', 'townhouse', 'residence'],
            'trust_score': 1.0,
        },
        'commercial': {
            'keywords': ['office', 'suite', 'floor', 'building', 'plaza', 'tower'],
            'trust_score': 0.5,
        },
        'po_box': {
            'keywords': ['po box', 'p.o. box', 'post office box'],
            'trust_score': 0.2,
        },
        'mail_drop': {
            'keywords': ['ups store', 'mailbox', 'mail center', 'postal annex', 'pak mail'],
            'trust_score': 0.1,
        },
    }
    
    def generate_verification_checklist(self, name: str, address: str,
                                          city: str, state: str, zip_code: str,
                                          phone: str = "") -> Dict[str, Any]:
        """
        Generate an OSINT verification checklist for the operator.
        The operator manually executes the queries and reports results.
        """
        checklist = {
            'target_identity': {
                'name': name,
                'address': address,
                'city': city,
                'state': state,
                'zip': zip_code,
                'phone': phone,
            },
            'verification_steps': [],
            'address_type_check': self._classify_address_type(address),
        }
        
        for source_id, source in self.OSINT_SOURCES.items():
            query = source['query_format'].format(
                name=name, address=address, city=city,
                state=state, zip=zip_code, phone=phone,
            )
            checklist['verification_steps'].append({
                'source': source['name'],
                'url': source['url'],
                'query': query,
                'checks': source['checks'],
                'reliability': source['reliability'],
                'status': 'pending',
            })
        
        return checklist
    
    def evaluate_results(self, person_exists: bool, address_match: bool,
                          phone_valid: bool, address_type: str,
                          sources_checked: int = 1) -> OSINTReport:
        """
        Evaluate OSINT results after operator completes verification.
        Returns confidence score and recommendation.
        """
        addr_trust = self.ADDRESS_TYPE_INDICATORS.get(
            address_type, {'trust_score': 0.5}
        )['trust_score']
        
        score = 0.0
        if person_exists:
            score += 0.35
        if address_match:
            score += 0.30
        if phone_valid:
            score += 0.15
        score *= addr_trust
        # Bonus for multiple sources
        score += min(sources_checked * 0.05, 0.20)
        score = min(score, 1.0)
        
        if score >= 0.70:
            result = OSINTVerificationResult.CONFIRMED
            recommendation = "OSINT CONFIRMED — high confidence. Proceed with transaction."
        elif score >= 0.40:
            result = OSINTVerificationResult.PARTIAL
            recommendation = "PARTIAL match — verify missing fields before proceeding."
        elif person_exists:
            result = OSINTVerificationResult.UNVERIFIED
            recommendation = "Person exists but address/phone unverified — higher risk."
        else:
            result = OSINTVerificationResult.MISMATCH
            recommendation = "OSINT MISMATCH — identity may be fabricated. Do not proceed."
        
        return OSINTReport(
            person_exists=person_exists,
            address_match=address_match,
            phone_valid=phone_valid,
            address_type=address_type,
            confidence_score=round(score, 2),
            result=result,
            sources_checked=[f"source_{i}" for i in range(sources_checked)],
            recommendation=recommendation,
        )
    
    def _classify_address_type(self, address: str) -> Dict[str, Any]:
        """Classify address as residential, commercial, PO box, or mail drop"""
        addr_lower = address.lower()
        for addr_type, info in self.ADDRESS_TYPE_INDICATORS.items():
            for keyword in info['keywords']:
                if keyword in addr_lower:
                    return {
                        'type': addr_type,
                        'trust_score': info['trust_score'],
                        'matched_keyword': keyword,
                    }
        # Default: assume residential if no commercial indicators
        return {'type': 'residential', 'trust_score': 1.0, 'matched_keyword': None}


# ═══════════════════════════════════════════════════════════════════════════
# V7.0 HARDENING: CARD QUALITY GRADING
# Research §6.3: 'Cerberus assigns a quality grade to each card based
# on its BIN data and validation results.'
# ═══════════════════════════════════════════════════════════════════════════

class CardQualityGrade(Enum):
    PREMIUM = "PREMIUM"      # 85-95% success
    DEGRADED = "DEGRADED"    # 30-50% success
    LOW = "LOW"              # 10-25% success


@dataclass
class CardQualityReport:
    """Card quality assessment with success rate prediction"""
    grade: CardQualityGrade
    success_rate_estimate: str
    bin_score: Optional[BINScore]
    avs_result: Optional[AVSCheckResult]
    osint_result: Optional[OSINTReport]
    geo_consistent: bool
    risk_factors: List[str]
    recommendation: str


class CardQualityGrader:
    """
    Assigns PREMIUM / DEGRADED / LOW grade to a card based on
    combined BIN score, AVS result, OSINT verification, and geo match.
    """
    
    def grade_card(self, bin_score: BINScore,
                    avs_result: Optional[AVSCheckResult] = None,
                    osint_result: Optional[OSINTReport] = None,
                    geo_consistent: bool = True) -> CardQualityReport:
        """Generate comprehensive card quality report"""
        
        risk_factors = list(bin_score.risk_factors)
        points = bin_score.overall_score  # Start from BIN score (0-100)
        
        # AVS adjustment
        if avs_result:
            if avs_result.avs_code == AVSResult.FULL_MATCH:
                points += 5
            elif avs_result.avs_code == AVSResult.ZIP_MATCH:
                points -= 5
            elif avs_result.avs_code == AVSResult.NO_MATCH:
                points -= 30
                risk_factors.append("AVS NO MATCH — high decline probability")
        
        # OSINT adjustment
        if osint_result:
            if osint_result.result == OSINTVerificationResult.CONFIRMED:
                points += 10
            elif osint_result.result == OSINTVerificationResult.MISMATCH:
                points -= 25
                risk_factors.append("OSINT identity mismatch")
            if osint_result.address_type in ('po_box', 'mail_drop'):
                points -= 15
                risk_factors.append(f"Address is {osint_result.address_type} — low trust")
        
        # Geo adjustment
        if not geo_consistent:
            points -= 20
            risk_factors.append("Geo mismatch: IP/timezone does not match billing")
        
        # Determine grade
        points = max(0, min(100, points))
        
        if points >= 75:
            grade = CardQualityGrade.PREMIUM
            success_rate = "85-95%"
            recommendation = (f"PREMIUM card — {bin_score.bank} {bin_score.card_level.replace('_',' ').title()} "
                            f"{bin_score.network.upper()}. Suitable for high-value targets.")
        elif points >= 45:
            grade = CardQualityGrade.DEGRADED
            success_rate = "30-50%"
            recommendation = (f"DEGRADED — usable but limited. Best for low-friction digital targets. "
                            f"Fix: {'; '.join(risk_factors[:2])}")
        else:
            grade = CardQualityGrade.LOW
            success_rate = "10-25%"
            recommendation = (f"LOW quality — high decline risk. Consider alternative card. "
                            f"Issues: {'; '.join(risk_factors[:3])}")
        
        return CardQualityReport(
            grade=grade,
            success_rate_estimate=success_rate,
            bin_score=bin_score,
            avs_result=avs_result,
            osint_result=osint_result,
            geo_consistent=geo_consistent,
            risk_factors=risk_factors,
            recommendation=recommendation,
        )


# ═══════════════════════════════════════════════════════════════════════════
# V7.0.2: ISSUING BANK PATTERN PREDICTOR
# Targets: 35% of declines (issuing bank out-of-pattern decisions)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PatternPrediction:
    """Issuing bank pattern match prediction"""
    in_pattern: bool
    confidence: float               # 0-1
    risk_level: str                 # low, medium, high, critical
    pattern_score: float            # 0-100
    warnings: List[str]
    recommendations: List[str]
    optimal_amount_range: Tuple[float, float]
    optimal_time_window: str        # e.g. "Weekday 10am-6pm EST"
    merchant_category_risk: str     # low, medium, high


class IssuingBankPatternPredictor:
    """
    V7.0.2: Predicts whether a transaction will trigger the issuing bank's
    internal fraud model based on:
    - Card level → typical spending patterns
    - Merchant category → how common is this purchase for the cardholder demographic
    - Amount → does it fall within expected range for this card tier
    - Time of day → business hours vs late night
    - Transaction frequency → first purchase vs repeat
    
    Issuing bank declines are the #1 failure factor (35% of all declines).
    By filtering transactions that would likely be flagged, we avoid burning cards.
    """
    
    # Typical spending patterns by card level
    SPENDING_PATTERNS = {
        'centurion': {
            'typical_categories': ['travel', 'luxury', 'electronics', 'dining', 'retail'],
            'unusual_categories': ['gaming_keys', 'crypto', 'gift_cards'],
            'typical_amount': (200, 15000),
            'safe_amount': (100, 5000),
            'velocity_tolerance': 'high',       # Can handle multiple transactions
        },
        'platinum': {
            'typical_categories': ['travel', 'electronics', 'retail', 'dining', 'subscriptions'],
            'unusual_categories': ['crypto', 'gift_cards'],
            'typical_amount': (50, 5000),
            'safe_amount': (50, 2000),
            'velocity_tolerance': 'medium',
        },
        'signature': {
            'typical_categories': ['retail', 'electronics', 'dining', 'travel', 'subscriptions'],
            'unusual_categories': ['crypto'],
            'typical_amount': (20, 3000),
            'safe_amount': (30, 1000),
            'velocity_tolerance': 'medium',
        },
        'world_elite': {
            'typical_categories': ['travel', 'retail', 'electronics', 'dining'],
            'unusual_categories': ['crypto', 'gift_cards'],
            'typical_amount': (50, 8000),
            'safe_amount': (50, 3000),
            'velocity_tolerance': 'medium',
        },
        'world': {
            'typical_categories': ['retail', 'dining', 'subscriptions', 'electronics'],
            'unusual_categories': ['crypto', 'luxury'],
            'typical_amount': (10, 2000),
            'safe_amount': (20, 800),
            'velocity_tolerance': 'low',
        },
        'gold': {
            'typical_categories': ['retail', 'dining', 'subscriptions', 'gas'],
            'unusual_categories': ['travel', 'crypto', 'luxury'],
            'typical_amount': (10, 1500),
            'safe_amount': (15, 500),
            'velocity_tolerance': 'low',
        },
        'classic': {
            'typical_categories': ['retail', 'gas', 'dining', 'subscriptions', 'grocery'],
            'unusual_categories': ['travel', 'crypto', 'luxury', 'electronics'],
            'typical_amount': (5, 500),
            'safe_amount': (10, 250),
            'velocity_tolerance': 'very_low',
        },
        'standard': {
            'typical_categories': ['retail', 'gas', 'grocery', 'subscriptions'],
            'unusual_categories': ['travel', 'crypto', 'luxury', 'electronics'],
            'typical_amount': (5, 300),
            'safe_amount': (10, 150),
            'velocity_tolerance': 'very_low',
        },
    }
    
    # Merchant → category mapping
    MERCHANT_CATEGORIES = {
        'g2a.com': 'gaming_keys', 'eneba.com': 'gaming_keys',
        'kinguin.net': 'gaming_keys', 'cdkeys.com': 'gaming_keys',
        'instant-gaming.com': 'gaming_keys', 'driffle.com': 'gaming_keys',
        'gamivo.com': 'gaming_keys', 'fanatical.com': 'gaming_keys',
        'greenmangaming.com': 'gaming_keys', 'humblebundle.com': 'gaming_keys',
        'store.steampowered.com': 'gaming_platform',
        'store.playstation.com': 'gaming_platform',
        'xbox.com': 'gaming_platform',
        'amazon.com': 'retail', 'bestbuy.com': 'electronics',
        'walmart.com': 'retail', 'target.com': 'retail',
        'nordstrom.com': 'retail', 'sephora.com': 'retail',
        'priceline.com': 'travel', 'booking.com': 'travel',
        'bitrefill.com': 'crypto', 'coinsbee.com': 'crypto',
        'stockx.com': 'luxury', 'google.com': 'subscriptions',
        'cardcash.com': 'gift_cards', 'raise.com': 'gift_cards',
    }
    
    # Bank-specific fraud model aggressiveness
    BANK_AGGRESSIVENESS = {
        'Chase': 0.85,              # Very aggressive fraud detection
        'Bank of America': 0.80,
        'Wells Fargo': 0.75,
        'Capital One': 0.70,        # Moderate
        'Citi': 0.70,
        'US Bank': 0.65,
        'USAA': 0.60,               # Less aggressive (military demographic)
        'Navy Federal': 0.55,       # Less aggressive
        'Barclays': 0.65,
        'Monzo': 0.50,              # Fintech — fewer legacy rules
        'Revolut': 0.45,            # Fintech — most permissive
        'American Express': 0.90,   # Most aggressive
        'Discover': 0.60,
    }
    
    def predict(self, bin_number: str, merchant: str, amount: float,
                time_hour_utc: int = None) -> PatternPrediction:
        """
        Predict whether a transaction will be approved by the issuing bank.
        
        Args:
            bin_number: First 6 digits of card
            merchant: Merchant domain or name
            amount: Transaction amount in USD
            time_hour_utc: Hour of transaction (0-23 UTC). None = current
        """
        scorer = BINScoringEngine()
        bin_score = scorer.score_bin(bin_number)
        
        level = bin_score.card_level
        bank = bin_score.bank
        pattern = self.SPENDING_PATTERNS.get(level, self.SPENDING_PATTERNS['classic'])
        
        warnings = []
        recommendations = []
        score = 80.0  # Start at 80 (neutral)
        
        # 1. Merchant category analysis
        merchant_lower = merchant.lower().replace('www.', '')
        category = self.MERCHANT_CATEGORIES.get(merchant_lower, 'retail')
        
        if category in pattern.get('unusual_categories', []):
            score -= 25
            warnings.append(f"'{category}' is unusual for {level} cards — bank ML may flag")
            merchant_risk = 'high'
        elif category in pattern.get('typical_categories', []):
            score += 5
            merchant_risk = 'low'
        else:
            score -= 10
            merchant_risk = 'medium'
        
        # 2. Amount analysis
        safe_low, safe_high = pattern['safe_amount']
        typical_low, typical_high = pattern['typical_amount']
        
        if safe_low <= amount <= safe_high:
            score += 10
            recommendations.append(f"Amount ${amount:.0f} is in safe range for {level}")
        elif typical_low <= amount <= typical_high:
            score += 0  # Neutral
        elif amount > typical_high:
            over_ratio = amount / typical_high
            penalty = min(35, (over_ratio - 1) * 30)
            score -= penalty
            warnings.append(f"${amount:.0f} exceeds typical max ${typical_high:.0f} for {level} — {over_ratio:.1f}x over")
            recommendations.append(f"Reduce to ${safe_high:.0f} or below for safest approval")
        elif amount < typical_low:
            score -= 5  # Very low amounts can also be suspicious (testing)
            warnings.append(f"Very low amount ${amount:.0f} may look like card testing")
        
        # 3. Bank aggressiveness factor
        aggressiveness = self.BANK_AGGRESSIVENESS.get(bank, 0.65)
        if aggressiveness >= 0.80:
            score -= 10
            warnings.append(f"{bank} has aggressive fraud detection (score penalty -10)")
        elif aggressiveness <= 0.55:
            score += 5
            recommendations.append(f"{bank} has relaxed fraud model — favorable")
        
        # 4. Time analysis (banks flag late-night transactions)
        if time_hour_utc is not None:
            # Convert to US Eastern rough estimate
            est_hour = (time_hour_utc - 5) % 24
            if 2 <= est_hour <= 5:
                score -= 15
                warnings.append("Late-night transaction (2-5am EST) — elevated scrutiny")
                recommendations.append("Transact between 10am-8pm EST for lowest risk")
            elif 10 <= est_hour <= 18:
                score += 5  # Business hours — lowest risk
        
        # 5. Digital goods surcharge (banks know these categories)
        if category in ('gaming_keys', 'crypto', 'gift_cards'):
            score -= 10
            warnings.append(f"Digital goods category '{category}' has elevated chargeback rate — banks scrutinize more")
        
        # 6. First-time merchant penalty
        # (We can't know if the cardholder has shopped here, so assume first-time)
        score -= 5
        warnings.append("Assumed first-time purchase at this merchant (bank sees new merchant = +risk)")
        
        # Clamp score
        score = max(0, min(100, score))
        
        # Determine risk level
        if score >= 70:
            risk_level = 'low'
            in_pattern = True
        elif score >= 50:
            risk_level = 'medium'
            in_pattern = True
        elif score >= 30:
            risk_level = 'high'
            in_pattern = False
            recommendations.append("HIGH RISK — consider different card or lower amount")
        else:
            risk_level = 'critical'
            in_pattern = False
            recommendations.append("CRITICAL — this transaction will very likely be declined. Change card or target")
        
        # Optimal time window
        if bank in ('Chase', 'Bank of America', 'Wells Fargo', 'American Express'):
            optimal_time = "Weekday 10am-6pm EST (bank business hours)"
        else:
            optimal_time = "Weekday 9am-9pm EST"
        
        return PatternPrediction(
            in_pattern=in_pattern,
            confidence=round(aggressiveness, 2),
            risk_level=risk_level,
            pattern_score=round(score, 1),
            warnings=warnings,
            recommendations=recommendations,
            optimal_amount_range=(safe_low, safe_high),
            optimal_time_window=optimal_time,
            merchant_category_risk=merchant_risk,
        )


# ═══════════════════════════════════════════════════════════════════════════
# V7.0.2: MAXDRAIN STRATEGY ENGINE
# Post-validation optimal extraction planning
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DrainStep:
    """Single step in a drain sequence"""
    step_number: int
    phase: str                  # warmup, primary, secondary, cashout
    target: str                 # merchant domain
    category: str               # gaming_keys, gift_cards, electronics, travel, crypto
    amount: float               # USD
    product_type: str           # what to buy
    timing: str                 # when to execute relative to previous step
    delay_minutes: int          # minutes to wait after previous step
    priority: str               # critical, high, medium, optional
    success_probability: float  # 0-1
    cashout_rate: float         # resale value as % of purchase price
    notes: str = ""


@dataclass
class DrainPlan:
    """Complete drain strategy for a validated card"""
    card_bin: str
    card_level: str
    bank: str
    country: str
    estimated_limit: float          # max single transaction
    estimated_daily_limit: float    # daily velocity limit
    total_drain_target: float       # total planned extraction
    total_cashout_value: float      # estimated cashout after resale
    cashout_efficiency: float       # cashout_value / drain_target
    steps: List[DrainStep]
    velocity_rules: List[str]
    warnings: List[str]
    estimated_duration_hours: float
    risk_level: str                 # low, medium, high


class MaxDrainEngine:
    """
    V7.0.2: Generates optimal extraction strategy after CC validation.
    
    Takes BIN score + card details and produces a timed, multi-step drain
    plan that maximizes total value while staying within bank velocity
    limits and avoiding fraud triggers.
    
    Drain Phases:
        1. WARMUP: Small trust-building purchase ($5-20)
        2. PRIMARY: Main high-value extraction
        3. SECONDARY: Additional extraction on different merchants
        4. CASHOUT: Convert remaining limit to liquid assets
    
    Usage:
        engine = MaxDrainEngine()
        plan = engine.generate_plan("401200", amount_limit=2000)
        for step in plan.steps:
            print(f"Step {step.step_number}: {step.target} ${step.amount}")
    """
    
    # Drain targets organized by category with cashout rates
    DRAIN_TARGETS = {
        "gaming_keys": {
            "targets": [
                {"domain": "g2a.com", "max_single": 500, "cashout_rate": 0.75,
                 "products": "Steam/PSN/Xbox keys", "3ds_rate": 0.15,
                 "notes": "Split into multiple $50-100 key purchases for best resale"},
                {"domain": "eneba.com", "max_single": 500, "cashout_rate": 0.78,
                 "products": "Game keys, gift cards", "3ds_rate": 0.20,
                 "notes": "Adyen PSP — US cards have low 3DS"},
                {"domain": "instant-gaming.com", "max_single": 300, "cashout_rate": 0.72,
                 "products": "PC game keys", "3ds_rate": 0.18,
                 "notes": "Good for EU cards. Fast delivery."},
                {"domain": "cdkeys.com", "max_single": 250, "cashout_rate": 0.70,
                 "products": "Console/PC keys", "3ds_rate": 0.15,
                 "notes": "Low friction, fast key delivery"},
                {"domain": "gamivo.com", "max_single": 300, "cashout_rate": 0.73,
                 "products": "Game keys, subscriptions", "3ds_rate": 0.18,
                 "notes": "Good alternative when G2A/Eneba are down"},
            ],
            "category_cashout": 0.74,
            "velocity_safe": True,
            "notes": "Best cashout category. Keys delivered instantly. Resell on secondary markets.",
        },
        "gift_cards": {
            "targets": [
                {"domain": "mygiftcardsupply.com", "max_single": 500, "cashout_rate": 0.82,
                 "products": "Amazon/iTunes/Google Play GCs", "3ds_rate": 0.10,
                 "notes": "Stripe PSP, low 3DS on US cards. Amazon GC = best cashout"},
                {"domain": "cardcash.com", "max_single": 300, "cashout_rate": 0.80,
                 "products": "Various retailer gift cards", "3ds_rate": 0.15,
                 "notes": "Can also sell GCs here for cash"},
                {"domain": "raise.com", "max_single": 500, "cashout_rate": 0.85,
                 "products": "Discounted gift cards", "3ds_rate": 0.20,
                 "notes": "Higher 3DS but best resale rates"},
                {"domain": "bitrefill.com", "max_single": 1000, "cashout_rate": 0.88,
                 "products": "Crypto vouchers, phone top-ups", "3ds_rate": 0.12,
                 "notes": "Convert to crypto directly. Best for cashout."},
            ],
            "category_cashout": 0.84,
            "velocity_safe": True,
            "notes": "Highest cashout rate. Amazon GC and crypto vouchers are most liquid.",
        },
        "electronics": {
            "targets": [
                {"domain": "bestbuy.com", "max_single": 2000, "cashout_rate": 0.65,
                 "products": "GPUs, laptops, phones", "3ds_rate": 0.25,
                 "notes": "Ship to clean drop. Forter antifraud — needs warmup."},
                {"domain": "newegg.com", "max_single": 1500, "cashout_rate": 0.60,
                 "products": "Computer parts, peripherals", "3ds_rate": 0.15,
                 "notes": "Lower 3DS than Best Buy. Good for high-value single items."},
                {"domain": "walmart.com", "max_single": 1000, "cashout_rate": 0.55,
                 "products": "Electronics, consoles", "3ds_rate": 0.12,
                 "notes": "Store pickup avoids shipping fraud flags"},
                {"domain": "amazon.com", "max_single": 2000, "cashout_rate": 0.60,
                 "products": "Electronics, everything", "3ds_rate": 0.10,
                 "notes": "Needs aged account. Ship to locker or fresh drop."},
            ],
            "category_cashout": 0.60,
            "velocity_safe": False,
            "notes": "Higher value per transaction but lower cashout rate. Physical goods need drops.",
        },
        "travel": {
            "targets": [
                {"domain": "priceline.com", "max_single": 3000, "cashout_rate": 0.50,
                 "products": "Hotel bookings (refundable)", "3ds_rate": 0.20,
                 "notes": "Book refundable hotel → cancel → refund to different method"},
                {"domain": "booking.com", "max_single": 2000, "cashout_rate": 0.45,
                 "products": "Hotels, car rentals", "3ds_rate": 0.25,
                 "notes": "Free cancellation bookings. Adyen PSP."},
            ],
            "category_cashout": 0.48,
            "velocity_safe": True,
            "notes": "Good for high limits. Refundable bookings can be leveraged. Lower cashout.",
        },
        "crypto": {
            "targets": [
                {"domain": "bitrefill.com", "max_single": 1000, "cashout_rate": 0.90,
                 "products": "BTC/LN vouchers", "3ds_rate": 0.12,
                 "notes": "Best direct-to-crypto path. Lightning Network for speed."},
                {"domain": "coinsbee.com", "max_single": 500, "cashout_rate": 0.88,
                 "products": "Crypto gift cards", "3ds_rate": 0.15,
                 "notes": "Alternative to Bitrefill. Good for EU cards."},
            ],
            "category_cashout": 0.89,
            "velocity_safe": True,
            "notes": "Highest cashout efficiency. Direct to crypto = hardest to trace.",
        },
    }
    
    # Bank velocity rules — how fast you can drain without triggering alerts
    BANK_VELOCITY = {
        'Chase': {
            'max_transactions_1h': 2, 'max_transactions_24h': 5,
            'cooldown_minutes': 45, 'max_single_pct': 0.40,
            'alert_threshold': 0.60, 'notes': 'Aggressive fraud detection. Go slow.'
        },
        'Bank of America': {
            'max_transactions_1h': 2, 'max_transactions_24h': 5,
            'cooldown_minutes': 40, 'max_single_pct': 0.45,
            'alert_threshold': 0.55, 'notes': 'Similar to Chase. Text alerts enabled.'
        },
        'Wells Fargo': {
            'max_transactions_1h': 3, 'max_transactions_24h': 6,
            'cooldown_minutes': 30, 'max_single_pct': 0.50,
            'alert_threshold': 0.65, 'notes': 'Slightly more tolerant than Chase.'
        },
        'Capital One': {
            'max_transactions_1h': 3, 'max_transactions_24h': 7,
            'cooldown_minutes': 25, 'max_single_pct': 0.50,
            'alert_threshold': 0.60, 'notes': 'Moderate. Handles multiple merchants OK.'
        },
        'Citi': {
            'max_transactions_1h': 3, 'max_transactions_24h': 6,
            'cooldown_minutes': 30, 'max_single_pct': 0.50,
            'alert_threshold': 0.60, 'notes': 'Moderate velocity tolerance.'
        },
        'US Bank': {
            'max_transactions_1h': 3, 'max_transactions_24h': 7,
            'cooldown_minutes': 25, 'max_single_pct': 0.55,
            'alert_threshold': 0.65, 'notes': 'Regional bank — more tolerant.'
        },
        'USAA': {
            'max_transactions_1h': 4, 'max_transactions_24h': 8,
            'cooldown_minutes': 20, 'max_single_pct': 0.60,
            'alert_threshold': 0.70, 'notes': 'Military bank — relaxed fraud model.'
        },
        'Navy Federal': {
            'max_transactions_1h': 4, 'max_transactions_24h': 8,
            'cooldown_minutes': 20, 'max_single_pct': 0.60,
            'alert_threshold': 0.70, 'notes': 'Credit union — relaxed fraud model.'
        },
        'American Express': {
            'max_transactions_1h': 2, 'max_transactions_24h': 4,
            'cooldown_minutes': 60, 'max_single_pct': 0.35,
            'alert_threshold': 0.45, 'notes': 'MOST AGGRESSIVE. Go very slow. High limits but low tolerance.'
        },
        'Discover': {
            'max_transactions_1h': 3, 'max_transactions_24h': 7,
            'cooldown_minutes': 25, 'max_single_pct': 0.55,
            'alert_threshold': 0.65, 'notes': 'Moderate. No VBV (uses ProtectBuy).'
        },
        'Monzo': {
            'max_transactions_1h': 5, 'max_transactions_24h': 10,
            'cooldown_minutes': 15, 'max_single_pct': 0.65,
            'alert_threshold': 0.75, 'notes': 'Fintech — high velocity tolerance.'
        },
        'Revolut': {
            'max_transactions_1h': 5, 'max_transactions_24h': 10,
            'cooldown_minutes': 15, 'max_single_pct': 0.70,
            'alert_threshold': 0.80, 'notes': 'Fintech — most tolerant. But always 3DS.'
        },
    }
    
    # Default velocity for unknown banks
    DEFAULT_VELOCITY = {
        'max_transactions_1h': 3, 'max_transactions_24h': 6,
        'cooldown_minutes': 30, 'max_single_pct': 0.45,
        'alert_threshold': 0.60, 'notes': 'Unknown bank — use conservative pacing.'
    }
    
    def generate_plan(self, bin_number: str,
                      amount_limit: float = None,
                      preferred_categories: List[str] = None,
                      country: str = None,
                      time_hour_utc: int = None) -> DrainPlan:
        """
        Generate optimal drain plan for a validated card.
        
        Args:
            bin_number: First 6+ digits of card
            amount_limit: Override max amount (otherwise inferred from BIN)
            preferred_categories: Preferred drain categories (gaming_keys, gift_cards, etc.)
            country: Card country (overrides BIN inference)
            time_hour_utc: Current hour UTC for time-of-day optimization
        """
        # Get BIN intelligence
        scorer = BINScoringEngine()
        bin_score = scorer.score_bin(bin_number)
        
        bank = bin_score.bank
        card_level = bin_score.card_level
        card_country = country or bin_score.country
        
        # Determine limits
        max_single = amount_limit or bin_score.max_single_amount
        daily_limit = bin_score.velocity_limit_daily
        
        # Get velocity rules for this bank
        velocity = self.BANK_VELOCITY.get(bank, self.DEFAULT_VELOCITY)
        
        # Calculate safe extraction amounts
        # Never use more than alert_threshold % of daily limit
        safe_daily = daily_limit * velocity['alert_threshold']
        safe_single = max_single * velocity['max_single_pct']
        max_txns_24h = velocity['max_transactions_24h']
        cooldown = velocity['cooldown_minutes']
        
        # Select drain categories
        if preferred_categories:
            categories = [c for c in preferred_categories if c in self.DRAIN_TARGETS]
        else:
            # Default priority: crypto > gift_cards > gaming_keys > electronics > travel
            categories = ["crypto", "gift_cards", "gaming_keys", "electronics", "travel"]
        
        # Build the drain sequence
        steps = []
        total_planned = 0.0
        total_cashout = 0.0
        step_num = 0
        cumulative_delay = 0
        warnings = []
        
        # ── PHASE 1: WARMUP ──────────────────────────────────────────
        # Small trust-building purchase to test card and build merchant trust
        warmup_amount = min(random.uniform(8, 20), safe_single * 0.05)
        warmup_target = self._select_warmup_target(categories, card_country)
        
        if warmup_target:
            step_num += 1
            steps.append(DrainStep(
                step_number=step_num,
                phase="warmup",
                target=warmup_target["domain"],
                category="gaming_keys",
                amount=round(warmup_amount, 2),
                product_type="Low-value game key or small gift card",
                timing="Immediately — test card validity on real merchant",
                delay_minutes=0,
                priority="critical",
                success_probability=0.90,
                cashout_rate=warmup_target.get("cashout_rate", 0.70),
                notes="WARMUP: Confirm card works on real merchant before committing to larger purchases. "
                      "If this fails, STOP — card may be monitored.",
            ))
            total_planned += warmup_amount
            total_cashout += warmup_amount * warmup_target.get("cashout_rate", 0.70)
            cumulative_delay += cooldown
        
        # ── PHASE 2: PRIMARY DRAIN ───────────────────────────────────
        # Main extraction — largest purchases on best cashout targets
        remaining_budget = safe_daily - total_planned
        primary_count = min(2, max_txns_24h - 1)  # Reserve slots for secondary
        
        for i in range(primary_count):
            if remaining_budget <= 20:
                break
            
            # Select best target for this step
            target_info = self._select_primary_target(
                categories, remaining_budget, safe_single, card_country
            )
            if not target_info:
                break
            
            # Calculate optimal amount for this step
            step_amount = min(
                remaining_budget * 0.55 if i == 0 else remaining_budget * 0.80,
                safe_single,
                target_info["max_single"],
            )
            step_amount = round(max(25, step_amount), 2)
            
            step_num += 1
            steps.append(DrainStep(
                step_number=step_num,
                phase="primary",
                target=target_info["domain"],
                category=target_info.get("_category", "gaming_keys"),
                amount=step_amount,
                product_type=target_info["products"],
                timing=f"Wait {cooldown} min after previous step",
                delay_minutes=cumulative_delay,
                priority="critical",
                success_probability=max(0.50, 0.85 - target_info["3ds_rate"]),
                cashout_rate=target_info["cashout_rate"],
                notes=target_info.get("notes", ""),
            ))
            total_planned += step_amount
            total_cashout += step_amount * target_info["cashout_rate"]
            remaining_budget -= step_amount
            cumulative_delay += cooldown
        
        # ── PHASE 3: SECONDARY DRAIN ─────────────────────────────────
        # Additional extraction on different merchants to diversify
        secondary_slots = max_txns_24h - step_num - 1  # Reserve 1 for cashout
        
        for i in range(min(secondary_slots, 2)):
            if remaining_budget <= 20:
                break
            
            target_info = self._select_secondary_target(
                categories, remaining_budget, safe_single, card_country,
                [s.target for s in steps]  # Avoid same merchants
            )
            if not target_info:
                break
            
            step_amount = min(
                remaining_budget * 0.60,
                safe_single * 0.80,
                target_info["max_single"],
            )
            step_amount = round(max(20, step_amount), 2)
            
            step_num += 1
            steps.append(DrainStep(
                step_number=step_num,
                phase="secondary",
                target=target_info["domain"],
                category=target_info.get("_category", "gaming_keys"),
                amount=step_amount,
                product_type=target_info["products"],
                timing=f"Wait {cooldown} min after previous step",
                delay_minutes=cumulative_delay,
                priority="high",
                success_probability=max(0.45, 0.80 - target_info["3ds_rate"]),
                cashout_rate=target_info["cashout_rate"],
                notes=target_info.get("notes", ""),
            ))
            total_planned += step_amount
            total_cashout += step_amount * target_info["cashout_rate"]
            remaining_budget -= step_amount
            cumulative_delay += cooldown
        
        # ── PHASE 4: CASHOUT ─────────────────────────────────────────
        # Final step — convert remaining balance to most liquid asset
        if remaining_budget > 15 and step_num < max_txns_24h:
            cashout_target = self._select_cashout_target(remaining_budget, card_country)
            if cashout_target:
                cashout_amount = min(remaining_budget * 0.90, cashout_target["max_single"])
                cashout_amount = round(max(15, cashout_amount), 2)
                
                step_num += 1
                steps.append(DrainStep(
                    step_number=step_num,
                    phase="cashout",
                    target=cashout_target["domain"],
                    category="crypto" if "bitrefill" in cashout_target["domain"] else "gift_cards",
                    amount=cashout_amount,
                    product_type=cashout_target["products"],
                    timing=f"Wait {cooldown} min — final extraction",
                    delay_minutes=cumulative_delay,
                    priority="medium",
                    success_probability=max(0.40, 0.75 - cashout_target["3ds_rate"]),
                    cashout_rate=cashout_target["cashout_rate"],
                    notes="CASHOUT: Final extraction. Convert to most liquid asset. "
                          "If previous steps triggered alerts, this may decline.",
                ))
                total_planned += cashout_amount
                total_cashout += cashout_amount * cashout_target["cashout_rate"]
                cumulative_delay += cooldown
        
        # Build velocity rules
        velocity_rules = [
            f"Max {velocity['max_transactions_1h']} transactions per hour",
            f"Max {max_txns_24h} transactions per 24 hours",
            f"Wait minimum {cooldown} minutes between purchases",
            f"No single transaction above ${safe_single:.0f} ({velocity['max_single_pct']*100:.0f}% of card limit)",
            f"Total daily spend should not exceed ${safe_daily:.0f} ({velocity['alert_threshold']*100:.0f}% of daily limit)",
            f"Bank: {bank} — {velocity['notes']}",
        ]
        
        # Time-of-day warnings
        if time_hour_utc is not None:
            est_hour = (time_hour_utc - 5) % 24
            if 2 <= est_hour <= 6:
                warnings.append("LATE NIGHT (2-6am EST): Higher scrutiny from banks. "
                                "Delay if possible until 10am+ EST.")
            elif 10 <= est_hour <= 18:
                warnings.append("OPTIMAL TIME: Business hours EST — lowest bank scrutiny.")
        
        # Card-specific warnings
        if bank == 'American Express':
            warnings.append("AMEX: Most aggressive fraud detection. Use smallest amounts possible. "
                            "Consider splitting across 2 days.")
        if bin_score.card_type == 'debit':
            warnings.append("DEBIT CARD: Lower limits than credit. Real-time balance checking. "
                            "First decline = immediate block.")
        if bin_score.estimated_3ds_rate > 0.30:
            warnings.append(f"HIGH 3DS RATE ({bin_score.estimated_3ds_rate*100:.0f}%): "
                            "Card likely enrolled in VBV/MSC. Expect challenges on some merchants.")
        
        # Risk assessment
        if total_planned > safe_daily * 0.80:
            risk_level = "high"
            warnings.append("Drain plan uses >80% of safe daily limit. Consider splitting across 2 days.")
        elif total_planned > safe_daily * 0.50:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        duration_hours = cumulative_delay / 60.0
        
        return DrainPlan(
            card_bin=bin_number[:6],
            card_level=card_level,
            bank=bank,
            country=card_country,
            estimated_limit=max_single,
            estimated_daily_limit=daily_limit,
            total_drain_target=round(total_planned, 2),
            total_cashout_value=round(total_cashout, 2),
            cashout_efficiency=round(total_cashout / total_planned, 2) if total_planned > 0 else 0,
            steps=steps,
            velocity_rules=velocity_rules,
            warnings=warnings,
            estimated_duration_hours=round(duration_hours, 1),
            risk_level=risk_level,
        )
    
    def _select_warmup_target(self, categories, country):
        """Select best low-friction target for warmup purchase"""
        # Prefer gaming keys for warmup — instant delivery, low friction
        for cat in ["gaming_keys", "gift_cards"]:
            if cat in self.DRAIN_TARGETS:
                targets = self.DRAIN_TARGETS[cat]["targets"]
                # Sort by lowest 3DS rate
                sorted_t = sorted(targets, key=lambda t: t["3ds_rate"])
                if sorted_t:
                    return sorted_t[0]
        return None
    
    def _select_primary_target(self, categories, budget, safe_single, country):
        """Select best target for primary drain — highest cashout rate within budget"""
        best = None
        best_score = 0
        
        for cat in categories:
            if cat not in self.DRAIN_TARGETS:
                continue
            for target in self.DRAIN_TARGETS[cat]["targets"]:
                if target["max_single"] < 25:
                    continue
                # Score: cashout_rate weighted by success probability
                score = target["cashout_rate"] * (1 - target["3ds_rate"])
                if score > best_score:
                    best_score = score
                    best = {**target, "_category": cat}
        
        return best
    
    def _select_secondary_target(self, categories, budget, safe_single, country, used_domains):
        """Select target for secondary drain — different merchant from primary"""
        best = None
        best_score = 0
        
        for cat in categories:
            if cat not in self.DRAIN_TARGETS:
                continue
            for target in self.DRAIN_TARGETS[cat]["targets"]:
                if target["domain"] in used_domains:
                    continue
                if target["max_single"] < 20:
                    continue
                score = target["cashout_rate"] * (1 - target["3ds_rate"]) * 0.9
                if score > best_score:
                    best_score = score
                    best = {**target, "_category": cat}
        
        return best
    
    def _select_cashout_target(self, budget, country):
        """Select highest-efficiency cashout target"""
        # Prefer crypto > gift cards for cashout
        for cat in ["crypto", "gift_cards"]:
            if cat in self.DRAIN_TARGETS:
                targets = self.DRAIN_TARGETS[cat]["targets"]
                sorted_t = sorted(targets, key=lambda t: t["cashout_rate"], reverse=True)
                for t in sorted_t:
                    if t["max_single"] >= min(budget, 15):
                        return t
        return None
    
    def format_plan_text(self, plan: DrainPlan) -> str:
        """Format drain plan as readable text for GUI display"""
        lines = []
        lines.append("=" * 60)
        lines.append("  MAXDRAIN STRATEGY — EXTRACTION PLAN")
        lines.append("=" * 60)
        lines.append(f"  Card: {plan.card_bin}*** | {plan.bank} {plan.card_level.replace('_',' ').title()}")
        lines.append(f"  Country: {plan.country} | Risk: {plan.risk_level.upper()}")
        lines.append(f"  Est. Limit: ${plan.estimated_limit:,.0f} single / ${plan.estimated_daily_limit:,.0f} daily")
        lines.append("-" * 60)
        lines.append(f"  TOTAL DRAIN: ${plan.total_drain_target:,.2f}")
        lines.append(f"  EST. CASHOUT: ${plan.total_cashout_value:,.2f} ({plan.cashout_efficiency*100:.0f}% efficiency)")
        lines.append(f"  DURATION: ~{plan.estimated_duration_hours:.1f} hours ({len(plan.steps)} steps)")
        lines.append("=" * 60)
        
        for step in plan.steps:
            phase_icon = {"warmup": "🔥", "primary": "💰", "secondary": "💎", "cashout": "🏦"}.get(step.phase, "▶")
            lines.append("")
            lines.append(f"  {phase_icon} STEP {step.step_number}: {step.phase.upper()}")
            lines.append(f"     Target: {step.target}")
            lines.append(f"     Amount: ${step.amount:,.2f} → cashout ~${step.amount * step.cashout_rate:,.2f}")
            lines.append(f"     Buy: {step.product_type}")
            lines.append(f"     Timing: {step.timing}")
            lines.append(f"     Success: {step.success_probability*100:.0f}% | Priority: {step.priority}")
            if step.notes:
                lines.append(f"     Notes: {step.notes}")
        
        if plan.velocity_rules:
            lines.append("")
            lines.append("-" * 60)
            lines.append("  VELOCITY RULES:")
            for rule in plan.velocity_rules:
                lines.append(f"     • {rule}")
        
        if plan.warnings:
            lines.append("")
            lines.append("-" * 60)
            lines.append("  ⚠️ WARNINGS:")
            for w in plan.warnings:
                lines.append(f"     ⚠️ {w}")
        
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def check_avs(card_address, card_zip, card_state, input_address, input_zip, input_state):
    """Quick AVS check"""
    return AVSEngine().check_avs(card_address, card_zip, card_state, input_address, input_zip, input_state)

def score_bin(bin_number, target=None):
    """Quick BIN scoring"""
    return BINScoringEngine().score_bin(bin_number, target)

def get_silent_strategy(bin_number, bank):
    """Get silent validation strategy"""
    return SilentValidationEngine().get_validation_strategy(bin_number, bank)

def check_geo(billing_state, exit_ip_state, browser_timezone):
    """Quick geo consistency check"""
    return GeoMatchChecker().check_geo_consistency(billing_state, exit_ip_state, browser_timezone)

def predict_bank_pattern(bin_number, merchant, amount, time_hour_utc=None):
    """V7.0.2: Predict issuing bank approval likelihood"""
    return IssuingBankPatternPredictor().predict(bin_number, merchant, amount, time_hour_utc)

def generate_drain_plan(bin_number, amount_limit=None, preferred_categories=None, country=None):
    """V7.0.2: Generate optimal drain strategy for a validated card"""
    from datetime import datetime
    hour_utc = datetime.utcnow().hour
    return MaxDrainEngine().generate_plan(
        bin_number, amount_limit=amount_limit,
        preferred_categories=preferred_categories,
        country=country, time_hour_utc=hour_utc
    )

def format_drain_plan(plan):
    """V7.0.2: Format drain plan as readable text"""
    return MaxDrainEngine().format_plan_text(plan)
