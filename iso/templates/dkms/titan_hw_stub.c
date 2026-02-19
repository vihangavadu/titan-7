#include <linux/module.h>
#include <linux/kernel.h>
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("TITAN Hardware Shield Stub");
static int __init titan_hw_init(void) { printk(KERN_INFO "TITAN HW: Loaded\n"); return 0; }
static void __exit titan_hw_exit(void) { printk(KERN_INFO "TITAN HW: Unloaded\n"); }
module_init(titan_hw_init);
module_exit(titan_hw_exit);
