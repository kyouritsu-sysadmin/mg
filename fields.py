from pydantic import Field
from typing import Annotated



BuildingOverviewType = Annotated[
    str | None, 
    Field(
        description=(
            "Mainly information about the construction site where the cubicles are supposed to be installed. "
            "Information like site area, address, floors etc. "
            "It also includes construction type, whether it's New work or reconstruction or repair or service. "
            "Residential information."
        ),
        examples=["Site Area: 500sqm, Address: 123 Tokyo St, Type: New Work"]
    )
]


Standards  = Annotated[
    str | None,
    Field(
        description=(
            "Applicable standards, codes and regulations the power receiving / transformation "
            "(受変電) cubicle equipment conforms to. Look for a 適用規格 / 準拠規格 / 標準仕様 table or "
            "list, usually near the top of the spec sheet (仕様表) or the special specification "
            "(特記仕様書). Capture Japanese standard bodies and code numbers such as JIS, JEM, JEC, "
            "the cubicle standard JIS C 4620 (キュービクル式高圧受電設備), 電気設備技術基準, 内線規程, and the "
            "high-voltage receiving regulation 高圧受電設備規程 (JEAC 8011). Also note the receiving "
            "voltage / phase / frequency when stated (e.g. 6.6kV 3φ3W 60Hz)."
        ),
        examples=[
            {
                "cubicle_standard": "JIS C 4620 (キュービクル式高圧受電設備)",
                "applicable_codes": "電気設備技術基準, 内線規程, 高圧受電設備規程 (JEAC 8011)",
                "equipment_standards": "JIS / JEM / JEC",
                "receiving_voltage": "6.6kV 3φ3W 60Hz",
            }
        ]
    )
]
PaintingSpec = Annotated[
    str | None, Field(
        description=(
            "Paint / coating specification of the metal enclosure (外箱) and panels. Search the "
            "塗装 row of the 仕様表 or the finishing notes. Capture the coating method "
            "(メラミン樹脂焼付塗装 = melamine baked finish, 粉体塗装 = powder coating), the colour expressed "
            "as a Munsell value (マンセル値, e.g. 5Y7/1, 2.5Y8/1), any distinction between indoor "
            "(屋内用) and outdoor (屋外用) paint, the film thickness (膜厚, e.g. 30μm以上), and the "
            "undercoat / rust-prevention treatment (防錆処理, 溶融亜鉛めっき = hot-dip galvanizing). "
            "Goal: let the LLM recognise and pull both the colour spec and the process."
        ),
        examples=[
            {
                "paint_method": "メラミン樹脂焼付塗装 (melamine baked finish)",
                "munsell_color": "5Y7/1 (淡灰色)",
                "indoor_paint": "屋内用 マンセル 5Y7/1",
                "outdoor_paint": "屋外用 マンセル 2.5Y8/1, 耐候性塗装",
                "film_thickness": "標準膜厚 30μm 以上",
                "undercoat": "防錆処理 / 溶融亜鉛めっき鋼板",
            }
        ]
    )
]


EquipmentSpecs = Annotated[
    str| None, Field(
        description=(
            "Ratings and specifications of the individual electrical devices housed in the "
            "cubicle, taken from the 各機器仕様 table and the single line diagram (単線結線図). "
            "Capture each device with its voltage / current / breaking-capacity ratings: "
            "真空遮断器 (VCB), 高圧交流負荷開閉器 (LBS), 断路器 (DS), 計器用変成器 (VT/CT), 進相コンデンサ (SC) and "
            "its series reactor (直列リアクトル SR), 限流ヒューズ (PF), 変圧器 (Tr), 避雷器 (LA/SPD)."
        ),
        examples=[
            {
                "VCB": "真空遮断器 7.2kV 600A 12.5kA",
                "LBS": "高圧交流負荷開閉器 7.2kV 200A PF付",
                "SC": "進相コンデンサ 6.6kV 200kvar 直列リアクトル付 (SR 6%)",
                "VT": "計器用変圧器 6600/110V",
                "CT": "変流器 75/5A",
                "transformer": "Tr 1φ 6.6kV/210-105V 100kVA, Tr 3φ 6.6kV/210-105V 300kVA",
            }
        ]
    )
]

LegendInfo = Annotated[
    str| None, Field(
    description=(
        "The symbol legend (凡例) table printed on the single line diagram, mapping each "
        "drawing 記号 (symbol / abbreviation) to its 名称 (component name). Extract the full "
        "symbol-to-name dictionary so device callouts in the SLD can be resolved."
    ),
    examples=[
        {
            "VCB": "真空遮断器",
            "DS": "断路器",
            "LBS": "高圧交流負荷開閉器",
            "SC": "進相コンデンサ",
            "PF": "限流ヒューズ",
            "VT": "計器用変圧器",
            "CT": "変流器",
            "MCCB": "配線用遮断器",
            "SPD": "避雷器 (サージ保護デバイス)",
        }
    ]
)
]

SafetyMeasures = Annotated[
    str| None, Field(
        description=(
            "Protective and safety measures for the installation. Look across the spec notes "
            "and姿図 (layout figures) for: earthquake / seismic resistance (耐震, 重要度係数, "
            "アンカーボルト・基礎ボルト固定), disaster & fire prevention (防災 / 防火), bird-damage netting "
            "(鳥害ネット / 鳥よけ網), tip-over / fall prevention (転倒防止), lightning & surge protection "
            "(避雷器 / SPD), and grounding / earthing works (接地工事 A種・D種, インターンロック)."
        ),
    examples=[
        {
            "earthquake_resistance": "耐震設計 重要度係数1.0以上, 基礎ボルト (SUS製) で固定",
            "disaster_resistance": "防災対応, 自家用発電設備と連携",
            "bird_netting": "鳥害ネット設置 (本工事)",
            "fall_prevention": "転倒防止アンカー固定",
            "surge_protection": "SPD (避雷器) 設置 クラスI",
            "grounding": "接地工事 A種・D種",
            "salt_resistance_system" : "【耐塩ﾌｨﾙﾀｰ】"       
        }
    ]
    )
]

Manufacturing_Spec = Annotated[
    str| None,  Field(
    description=(
        "Fabrication / construction specification of the cubicle enclosure itself, from the "
        "製作仕様 notes and the reference figure (参考姿図). Capture the enclosure type "
        "(屋内用 / 屋外用キュービクル), the steel plate thickness (鋼板厚, e.g. t2.3 外箱 / t1.6 内部), "
        "overall dimensions (W×D×H, often marked 参考), self-standing / maintenance type "
        "(自立形, 前面保守), ventilation louvres (換気ガラリ), and the base channel / foundation "
        "(ベースチャンネル, 基礎は建築工事)."
    ),
    examples=[
        {
            "enclosure_type": "屋外用キュービクル 自立形",
            "steel_thickness": "鋼板厚 t2.3 (外箱), t1.6 (内部)",
            "dimensions": "W6,100 × D2,400 × H2,300 (参考寸法)",
            "structure": "前面保守形, 換気ガラリ付",
            "base": "ベースチャンネル / 基礎 (建築工事)",
        }
    ]
)
]

AdditionalSystem= Annotated[
    str| None, Field (
    description= (
        "Supplementary or connected systems beyond the core receiving equipment. Search for "
        "太陽光発電設備 (PV / solar) and its パワーコンディショナ (PCS, power conditioner), 蓄電池 "
        "(storage battery), 非常用自家発電設備 (emergency generator), 力率改善, and power "
        "monitoring / metering systems (電力監視システム, デジタル計測装置)."
    ),
    examples=[
        {
            "solar_pv": "太陽光発電設備 約100kW 系統連系",
            "power_conditioner": "パワーコンディショナ (PCS) 6.6kV 連系",
            "generator": "非常用自家発電設備",
            "monitoring": "電力監視システム / デジタル計測装置",
        }
    ]
)
]

FunctionalExplanation= Annotated[
    str| None, Field(
    description=(
        "Functional / operational description of how the equipment behaves. Capture protection "
        "relay operation (保護継電器: 過電流継電器 OCR, 地絡方向継電器 DGR, 不足電圧継電器 UVR, 過電圧継電器 OVR), "
        "interlocks (インターロック between 断路器 and VCB), control & switching sequence "
        "(ON/OFF 操作), demand monitoring (デマンド監視制御), and alarms / indications."
    ),
    examples=[
        {
            "protection_relay": "過電流継電器 (OCR), 地絡方向継電器 (DGR), 不足電圧継電器 (UVR) で保護",
            "interlock": "断路器と VCB 間インターロック",
            "demand_control": "デマンド監視制御",
            "operation": "VCB ON/OFF を制御盤にて操作",
        }
    ]
)
]

MaterialsInfo  = Annotated [
    str| None, Field(
    description= (
        "Materials of the wiring and conductive components. Capture high-voltage cables "
        "(高圧ケーブル CV / CVT with size, e.g. 6.6kV 38sq), low-voltage cables (低圧ケーブル CV 600V), "
        "main-circuit bus bars / conductors (主回路導体 銅バー CU), cable terminations "
        "(ケーブルヘッド / 端末処理材), grounding wire (接地線 IV, アース母線), and conduit / insulation "
        "materials."
    ),
    examples=[
        {
            "hv_cable": "高圧ケーブル CVT 6.6kV 38sq",
            "lv_cable": "低圧ケーブル CV 600V",
            "busbar": "主回路導体 銅バー (CU)",
            "cable_head": "ケーブルヘッド (端末処理材)",
            "earthing_wire": "接地線 IV / アース母線",
        }
    ]
)
]

