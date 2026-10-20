#include <stdio.h>

// Helper function to calculate tax
double calculate_tax(double amount, double rate) {
    double tax = amount * rate;
    return tax;
}

// Compute total invoice with discount and tax
double generate_invoice(double base_price, double discount_rate, double tax_rate) {
    double discount = base_price * discount_rate;
    double discounted_price = base_price - discount;
    double tax = calculate_tax(discounted_price, tax_rate);
    double final_total = discounted_price + tax;
    
    printf("Base: %.2f\n", base_price);
    printf("Discount: %.2f\n", discount);
    printf("Tax: %.2f\n", tax);
    printf("Total: %.2f\n", final_total);
    
    return final_total;
}

int main() {
    double price = 100.0;
    double disc = 0.10;
    double tax = 0.05;
    
    double total = generate_invoice(price, disc, tax);
    return 0;
}
