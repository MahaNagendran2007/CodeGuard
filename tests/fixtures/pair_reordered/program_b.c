#include <stdio.h>

// Forward declaration
double calculate_tax(double amount, double rate);

// Compute total invoice with discount and tax (defined first)
double generate_invoice(double base_price, double discount_rate, double tax_rate) {
    // Reordered independent variable initializations
    double discount = base_price * discount_rate;
    double discounted_price = base_price - discount;
    double tax = calculate_tax(discounted_price, tax_rate);
    double final_total = tax + discounted_price; // Reordered operands
    
    // Reordered print statements
    printf("Total: %.2f\n", final_total);
    printf("Tax: %.2f\n", tax);
    printf("Discount: %.2f\n", discount);
    printf("Base: %.2f\n", base_price);
    
    return final_total;
}

// Helper function defined after main caller
double calculate_tax(double amount, double rate) {
    double tax = amount * rate;
    return tax;
}

int main() {
    // Reordered local declarations
    double tax = 0.05;
    double disc = 0.10;
    double price = 100.0;
    
    double total = generate_invoice(price, disc, tax);
    return 0;
}
