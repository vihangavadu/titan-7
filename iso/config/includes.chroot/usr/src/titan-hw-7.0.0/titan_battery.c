/*
 * TITAN Synthetic Battery Module - Kernel-Level Power Supply Virtualization
 *
 * TITAN V7.0 SINGULARITY
 * Architecture: Virtual power_supply class driver with physics-based discharge
 *
 * Defeats "Power Fingerprinting" by exposing a synthetic battery via
 * /sys/class/power_supply/ with dynamic voltage decay, thermal correlation,
 * and valid state transitions (Discharging → Charging → Full).
 *
 * A static or absent battery on a "mobile" persona is an immediate detection
 * signal. This module creates a realistic Li-Ion discharge model.
 *
 * Compiled for Linux 5.x+ with CONFIG_POWER_SUPPLY=y
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/power_supply.h>
#include <linux/timer.h>
#include <linux/jiffies.h>
#include <linux/random.h>
#include <linux/slab.h>
#include <linux/fs.h>
#include <linux/version.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Dva.12");
MODULE_DESCRIPTION("TITAN V7.0 Synthetic Battery Module - Power Supply Virtualization");
MODULE_VERSION("7.0");

/* ============================================================================
 * Configuration — loaded from profile or defaults to Samsung Galaxy S23
 * ============================================================================ */

#define PROFILE_PATH "/opt/lucid-empire/profiles/active"

/* Default battery spec: Samsung Galaxy S23 (3900 mAh, 3.86V nominal) */
static int charge_full_design  = 3900000;  /* µAh */
static int voltage_max_design  = 4350000;  /* µV  (4.35V max charge) */
static int voltage_min_design  = 3400000;  /* µV  (3.40V cutoff) */
static int temp_ambient        = 250;      /* 0.1°C units → 25.0°C */
static int discharge_rate_ua   = 450000;   /* µA average draw (~450mA) */
static char *manufacturer      = "Samsung SDI";
static char *model_name        = "EB-BG991ABY";
static char *serial_number     = "A1B2C3D4E5F6";

module_param(charge_full_design, int, 0644);
module_param(voltage_max_design, int, 0644);
module_param(voltage_min_design, int, 0644);
module_param(temp_ambient, int, 0644);
module_param(discharge_rate_ua, int, 0644);
module_param(manufacturer, charp, 0644);
module_param(model_name, charp, 0644);
module_param(serial_number, charp, 0644);

MODULE_PARM_DESC(charge_full_design, "Battery full capacity in µAh");
MODULE_PARM_DESC(voltage_max_design, "Maximum voltage in µV");
MODULE_PARM_DESC(voltage_min_design, "Minimum voltage in µV");
MODULE_PARM_DESC(temp_ambient, "Ambient temperature in 0.1°C");
MODULE_PARM_DESC(discharge_rate_ua, "Average discharge current in µA");
MODULE_PARM_DESC(manufacturer, "Battery manufacturer string");
MODULE_PARM_DESC(model_name, "Battery model name");
MODULE_PARM_DESC(serial_number, "Battery serial number");

/* ============================================================================
 * Internal State
 * ============================================================================ */

struct titan_battery_state {
    struct power_supply *psy;
    struct power_supply_desc psy_desc;
    struct timer_list update_timer;

    /* Dynamic state */
    int status;           /* POWER_SUPPLY_STATUS_DISCHARGING / CHARGING / FULL */
    int capacity;         /* 0-100 percent */
    int voltage_now;      /* µV */
    int current_now;      /* µA (negative = discharging) */
    int charge_now;       /* µAh */
    int temp;             /* 0.1°C */
    int cycle_count;      /* Charge cycles */
    int health;           /* POWER_SUPPLY_HEALTH_GOOD */

    /* Simulation parameters */
    unsigned long start_jiffies;
    int initial_capacity;
};

static struct titan_battery_state *bat_state;

/* ============================================================================
 * Physics-Based Discharge Model
 *
 * Li-Ion voltage curve approximation:
 *   V(soc) = Vmin + (Vmax - Vmin) * f(soc)
 *   where f(soc) is a piecewise function:
 *     soc > 90%: steep initial drop
 *     20% < soc < 90%: relatively flat plateau
 *     soc < 20%: steep final drop
 *
 * This creates the characteristic Li-Ion "flat middle" discharge profile
 * that detection systems validate.
 * ============================================================================ */

static int soc_to_voltage(int soc)
{
    int range = voltage_max_design - voltage_min_design;
    int voltage;

    if (soc > 90) {
        /* Steep initial region: 100% → 90% maps to ~95-100% of voltage range */
        voltage = voltage_max_design - (range * (100 - soc) / 100);
    } else if (soc > 20) {
        /* Flat plateau: 90% → 20% maps to ~15-95% of voltage range */
        int plateau_start = voltage_max_design - (range * 5 / 100);
        int plateau_end   = voltage_min_design + (range * 15 / 100);
        voltage = plateau_end + (plateau_start - plateau_end) * (soc - 20) / 70;
    } else {
        /* Steep final drop: 20% → 0% maps to 0-15% of voltage range */
        voltage = voltage_min_design + (range * 15 * soc / 100 / 20);
    }

    return voltage;
}

/* Add Gaussian-like jitter (±5mV) using kernel PRNG */
static int add_voltage_jitter(int voltage)
{
    int jitter;
    get_random_bytes(&jitter, sizeof(jitter));
    jitter = (jitter % 10000) - 5000;  /* ±5000 µV = ±5mV */
    return voltage + jitter;
}

/* Temperature model: ambient + CPU-correlated delta + random noise */
static int compute_temperature(void)
{
    int delta, noise;

    /* Simulate thermal load correlation (±2-5°C based on "load") */
    get_random_bytes(&delta, sizeof(delta));
    delta = (delta % 30) + 10;  /* 1.0 - 4.0°C above ambient */

    /* Micro-noise (±0.3°C) */
    get_random_bytes(&noise, sizeof(noise));
    noise = (noise % 6) - 3;  /* ±0.3°C */

    return temp_ambient + delta + noise;
}

/* Current draw model: base rate with ±10% jitter */
static int compute_current(int status)
{
    int jitter;

    if (status == POWER_SUPPLY_STATUS_FULL)
        return 0;

    get_random_bytes(&jitter, sizeof(jitter));
    jitter = (jitter % (discharge_rate_ua / 5)) - (discharge_rate_ua / 10);

    if (status == POWER_SUPPLY_STATUS_CHARGING)
        return discharge_rate_ua + jitter;  /* Positive = charging */

    return -(discharge_rate_ua + jitter);   /* Negative = discharging */
}

/* ============================================================================
 * Timer Callback — Updates battery state every 30 seconds
 * ============================================================================ */

static void titan_battery_update(struct timer_list *t)
{
    struct titan_battery_state *bs = from_timer(bs, t, update_timer);
    unsigned long elapsed_secs;

    elapsed_secs = (jiffies - bs->start_jiffies) / HZ;

    if (bs->status == POWER_SUPPLY_STATUS_DISCHARGING) {
        /* Compute capacity loss based on elapsed time */
        long ua_seconds = (long)discharge_rate_ua * elapsed_secs;
        long uah_consumed = ua_seconds / 3600;
        int new_charge = charge_full_design - (int)uah_consumed;

        if (new_charge < 0)
            new_charge = 0;

        bs->charge_now = new_charge;
        bs->capacity = (int)((long)new_charge * 100 / charge_full_design);

        if (bs->capacity < 0)
            bs->capacity = 0;
        if (bs->capacity > 100)
            bs->capacity = 100;
    } else if (bs->status == POWER_SUPPLY_STATUS_CHARGING) {
        /* Simulate charging: ~1% per 30 seconds for fast charge */
        if (bs->capacity < 100) {
            bs->capacity += 1;
            bs->charge_now = (int)((long)charge_full_design * bs->capacity / 100);
        }
        if (bs->capacity >= 100) {
            bs->capacity = 100;
            bs->charge_now = charge_full_design;
            bs->status = POWER_SUPPLY_STATUS_FULL;
        }
    }

    /* Update dynamic values */
    bs->voltage_now = add_voltage_jitter(soc_to_voltage(bs->capacity));
    bs->current_now = compute_current(bs->status);
    bs->temp = compute_temperature();

    /* Notify userspace of changes */
    power_supply_changed(bs->psy);

    /* Re-arm timer: 30 second update interval */
    mod_timer(&bs->update_timer, jiffies + 30 * HZ);
}

/* ============================================================================
 * Power Supply Properties
 * ============================================================================ */

static enum power_supply_property titan_battery_props[] = {
    POWER_SUPPLY_PROP_STATUS,
    POWER_SUPPLY_PROP_HEALTH,
    POWER_SUPPLY_PROP_PRESENT,
    POWER_SUPPLY_PROP_TECHNOLOGY,
    POWER_SUPPLY_PROP_CYCLE_COUNT,
    POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN,
    POWER_SUPPLY_PROP_VOLTAGE_MIN_DESIGN,
    POWER_SUPPLY_PROP_VOLTAGE_NOW,
    POWER_SUPPLY_PROP_CURRENT_NOW,
    POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN,
    POWER_SUPPLY_PROP_CHARGE_FULL,
    POWER_SUPPLY_PROP_CHARGE_NOW,
    POWER_SUPPLY_PROP_CAPACITY,
    POWER_SUPPLY_PROP_TEMP,
    POWER_SUPPLY_PROP_MANUFACTURER,
    POWER_SUPPLY_PROP_MODEL_NAME,
    POWER_SUPPLY_PROP_SERIAL_NUMBER,
};

static int titan_battery_get_property(struct power_supply *psy,
                                       enum power_supply_property psp,
                                       union power_supply_propval *val)
{
    struct titan_battery_state *bs = power_supply_get_drvdata(psy);

    switch (psp) {
    case POWER_SUPPLY_PROP_STATUS:
        val->intval = bs->status;
        break;
    case POWER_SUPPLY_PROP_HEALTH:
        val->intval = bs->health;
        break;
    case POWER_SUPPLY_PROP_PRESENT:
        val->intval = 1;
        break;
    case POWER_SUPPLY_PROP_TECHNOLOGY:
        val->intval = POWER_SUPPLY_TECHNOLOGY_LION;
        break;
    case POWER_SUPPLY_PROP_CYCLE_COUNT:
        val->intval = bs->cycle_count;
        break;
    case POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN:
        val->intval = voltage_max_design;
        break;
    case POWER_SUPPLY_PROP_VOLTAGE_MIN_DESIGN:
        val->intval = voltage_min_design;
        break;
    case POWER_SUPPLY_PROP_VOLTAGE_NOW:
        val->intval = bs->voltage_now;
        break;
    case POWER_SUPPLY_PROP_CURRENT_NOW:
        val->intval = bs->current_now;
        break;
    case POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN:
        val->intval = charge_full_design;
        break;
    case POWER_SUPPLY_PROP_CHARGE_FULL:
        val->intval = charge_full_design;  /* Assume healthy battery */
        break;
    case POWER_SUPPLY_PROP_CHARGE_NOW:
        val->intval = bs->charge_now;
        break;
    case POWER_SUPPLY_PROP_CAPACITY:
        val->intval = bs->capacity;
        break;
    case POWER_SUPPLY_PROP_TEMP:
        val->intval = bs->temp;
        break;
    case POWER_SUPPLY_PROP_MANUFACTURER:
        val->strval = manufacturer;
        break;
    case POWER_SUPPLY_PROP_MODEL_NAME:
        val->strval = model_name;
        break;
    case POWER_SUPPLY_PROP_SERIAL_NUMBER:
        val->strval = serial_number;
        break;
    default:
        return -EINVAL;
    }
    return 0;
}

/* Allow userspace to set status (Charging/Discharging) via sysfs */
static int titan_battery_set_property(struct power_supply *psy,
                                       enum power_supply_property psp,
                                       const union power_supply_propval *val)
{
    struct titan_battery_state *bs = power_supply_get_drvdata(psy);

    switch (psp) {
    case POWER_SUPPLY_PROP_STATUS:
        if (val->intval == POWER_SUPPLY_STATUS_CHARGING ||
            val->intval == POWER_SUPPLY_STATUS_DISCHARGING ||
            val->intval == POWER_SUPPLY_STATUS_FULL) {
            bs->status = val->intval;
            /* Reset simulation clock on state change */
            bs->start_jiffies = jiffies;
            power_supply_changed(bs->psy);
        }
        break;
    case POWER_SUPPLY_PROP_CAPACITY:
        if (val->intval >= 0 && val->intval <= 100) {
            bs->capacity = val->intval;
            bs->charge_now = (int)((long)charge_full_design * bs->capacity / 100);
            bs->voltage_now = soc_to_voltage(bs->capacity);
            bs->start_jiffies = jiffies;
            power_supply_changed(bs->psy);
        }
        break;
    default:
        return -EINVAL;
    }
    return 0;
}

static int titan_battery_property_is_writeable(struct power_supply *psy,
                                                enum power_supply_property psp)
{
    return (psp == POWER_SUPPLY_PROP_STATUS ||
            psp == POWER_SUPPLY_PROP_CAPACITY);
}

/* ============================================================================
 * Module Init / Exit
 * ============================================================================ */

static const struct power_supply_config titan_psy_cfg = { 0 };

static int __init titan_battery_init(void)
{
    struct power_supply_config cfg = { 0 };
    int initial_soc = 78;  /* Start at 78% — realistic "in-use" state */

    pr_info("TITAN Battery Shield: Initializing synthetic power supply...\n");

    bat_state = kzalloc(sizeof(*bat_state), GFP_KERNEL);
    if (!bat_state)
        return -ENOMEM;

    /* Initialize state */
    bat_state->status      = POWER_SUPPLY_STATUS_DISCHARGING;
    bat_state->health      = POWER_SUPPLY_HEALTH_GOOD;
    bat_state->capacity    = initial_soc;
    bat_state->charge_now  = (int)((long)charge_full_design * initial_soc / 100);
    bat_state->voltage_now = soc_to_voltage(initial_soc);
    bat_state->current_now = -discharge_rate_ua;
    bat_state->temp        = temp_ambient + 15;  /* Slightly warm from "use" */
    bat_state->cycle_count = 127;  /* Realistic cycle count for ~6 month old device */
    bat_state->start_jiffies    = jiffies;
    bat_state->initial_capacity = initial_soc;

    /* Power supply descriptor */
    bat_state->psy_desc.name           = "BAT0";
    bat_state->psy_desc.type           = POWER_SUPPLY_TYPE_BATTERY;
    bat_state->psy_desc.properties     = titan_battery_props;
    bat_state->psy_desc.num_properties = ARRAY_SIZE(titan_battery_props);
    bat_state->psy_desc.get_property   = titan_battery_get_property;
    bat_state->psy_desc.set_property   = titan_battery_set_property;
    bat_state->psy_desc.property_is_writeable = titan_battery_property_is_writeable;

    cfg.drv_data = bat_state;

    bat_state->psy = power_supply_register(NULL, &bat_state->psy_desc, &cfg);
    if (IS_ERR(bat_state->psy)) {
        pr_err("TITAN Battery Shield: Failed to register power supply\n");
        kfree(bat_state);
        return PTR_ERR(bat_state->psy);
    }

    /* Start periodic update timer */
    timer_setup(&bat_state->update_timer, titan_battery_update, 0);
    mod_timer(&bat_state->update_timer, jiffies + 30 * HZ);

    pr_info("TITAN Battery Shield: Registered BAT0 (%s %s)\n", manufacturer, model_name);
    pr_info("TITAN Battery Shield: Initial SOC=%d%% V=%dmV T=%d.%d°C\n",
            initial_soc,
            bat_state->voltage_now / 1000,
            bat_state->temp / 10, bat_state->temp % 10);

    return 0;
}

static void __exit titan_battery_exit(void)
{
    del_timer_sync(&bat_state->update_timer);
    power_supply_unregister(bat_state->psy);
    kfree(bat_state);
    pr_info("TITAN Battery Shield: Module unloaded\n");
}

module_init(titan_battery_init);
module_exit(titan_battery_exit);

MODULE_INFO(vermagic, VERMAGIC_STRING);
