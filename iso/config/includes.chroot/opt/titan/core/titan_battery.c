/*
 * TITAN V7.0.3 — Battery API Synthesis Module
 *
 * Synthesizes a Windows-compliant ACPI battery interface via sysfs.
 * Linux and Windows report battery status differently; VMs often report
 * "100% charged" or "no battery present" — a high-risk anomaly for a
 * residential user profile.
 *
 * This module creates /sys/class/power_supply/BAT0/ entries that report
 * realistic discharge rates, cycle counts, and charging states matching
 * a consumer laptop.  The Battery Status API (navigator.getBattery()) in
 * the browser reads from these sysfs nodes.
 *
 * Build: make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
 * Load:  insmod titan_battery.ko
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/power_supply.h>
#include <linux/random.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("TITAN");
MODULE_DESCRIPTION("Battery API Synthesis for anti-fingerprinting");
MODULE_VERSION("7.0.3");

/* Simulated battery state — realistic consumer laptop values */
static int battery_capacity = 78;       /* 78% — not suspiciously full */
static int battery_voltage_now = 11400; /* 11.4V — typical 3-cell Li-ion */
static int battery_voltage_full = 12600;
static int battery_current_now = -1250; /* Negative = discharging (mA) */
static int battery_cycle_count = 142;   /* Realistic for ~2yr old laptop */
static int battery_charge_full = 47500; /* 47.5 Wh design capacity */
static int battery_charge_now = 37050;  /* Matches 78% of full */
static int battery_status = POWER_SUPPLY_STATUS_DISCHARGING;

/* Micro-drift: prevent static values across sessions */
static void randomize_battery_state(void)
{
    unsigned int r;
    get_random_bytes(&r, sizeof(r));

    /* Capacity drifts 72-89% */
    battery_capacity = 72 + (r % 18);
    battery_charge_now = battery_charge_full * battery_capacity / 100;

    /* Current draw varies -800 to -2100 mA */
    battery_current_now = -(800 + (r >> 8) % 1300);

    /* Cycle count 80-300 */
    battery_cycle_count = 80 + (r >> 16) % 220;

    /* 70% chance discharging, 25% charging, 5% full */
    if ((r >> 24) < 179)
        battery_status = POWER_SUPPLY_STATUS_DISCHARGING;
    else if ((r >> 24) < 243)
        battery_status = POWER_SUPPLY_STATUS_CHARGING;
    else
        battery_status = POWER_SUPPLY_STATUS_FULL;
}

static int titan_bat_get_property(struct power_supply *psy,
                                  enum power_supply_property psp,
                                  union power_supply_propval *val)
{
    switch (psp) {
    case POWER_SUPPLY_PROP_STATUS:
        val->intval = battery_status;
        break;
    case POWER_SUPPLY_PROP_PRESENT:
        val->intval = 1;
        break;
    case POWER_SUPPLY_PROP_TECHNOLOGY:
        val->intval = POWER_SUPPLY_TECHNOLOGY_LION;
        break;
    case POWER_SUPPLY_PROP_CYCLE_COUNT:
        val->intval = battery_cycle_count;
        break;
    case POWER_SUPPLY_PROP_VOLTAGE_NOW:
        val->intval = battery_voltage_now * 1000; /* uV */
        break;
    case POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN:
        val->intval = battery_voltage_full * 1000;
        break;
    case POWER_SUPPLY_PROP_CURRENT_NOW:
        val->intval = battery_current_now * 1000; /* uA */
        break;
    case POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN:
        val->intval = battery_charge_full * 1000; /* uAh */
        break;
    case POWER_SUPPLY_PROP_CHARGE_FULL:
        val->intval = battery_charge_full * 1000;
        break;
    case POWER_SUPPLY_PROP_CHARGE_NOW:
        val->intval = battery_charge_now * 1000;
        break;
    case POWER_SUPPLY_PROP_CAPACITY:
        val->intval = battery_capacity;
        break;
    case POWER_SUPPLY_PROP_MODEL_NAME:
        val->strval = "DELL 7V69Y53";
        break;
    case POWER_SUPPLY_PROP_MANUFACTURER:
        val->strval = "Samsung SDI";
        break;
    default:
        return -EINVAL;
    }
    return 0;
}

static enum power_supply_property titan_bat_props[] = {
    POWER_SUPPLY_PROP_STATUS,
    POWER_SUPPLY_PROP_PRESENT,
    POWER_SUPPLY_PROP_TECHNOLOGY,
    POWER_SUPPLY_PROP_CYCLE_COUNT,
    POWER_SUPPLY_PROP_VOLTAGE_NOW,
    POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN,
    POWER_SUPPLY_PROP_CURRENT_NOW,
    POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN,
    POWER_SUPPLY_PROP_CHARGE_FULL,
    POWER_SUPPLY_PROP_CHARGE_NOW,
    POWER_SUPPLY_PROP_CAPACITY,
    POWER_SUPPLY_PROP_MODEL_NAME,
    POWER_SUPPLY_PROP_MANUFACTURER,
};

static const struct power_supply_desc titan_bat_desc = {
    .name           = "BAT0",
    .type           = POWER_SUPPLY_TYPE_BATTERY,
    .properties     = titan_bat_props,
    .num_properties = ARRAY_SIZE(titan_bat_props),
    .get_property   = titan_bat_get_property,
};

static struct power_supply *titan_bat_psy;

static int __init titan_battery_init(void)
{
    struct power_supply_config cfg = {};

    randomize_battery_state();

    titan_bat_psy = power_supply_register(NULL, &titan_bat_desc, &cfg);
    if (IS_ERR(titan_bat_psy)) {
        pr_err("titan_battery: Failed to register power supply\n");
        return PTR_ERR(titan_bat_psy);
    }

    pr_info("titan_battery: Synthetic BAT0 registered (cap=%d%% cyc=%d)\n",
            battery_capacity, battery_cycle_count);
    return 0;
}

static void __exit titan_battery_exit(void)
{
    if (titan_bat_psy)
        power_supply_unregister(titan_bat_psy);
    pr_info("titan_battery: Synthetic BAT0 unregistered\n");
}

module_init(titan_battery_init);
module_exit(titan_battery_exit);
