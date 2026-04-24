import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { AuthService } from '../../../../features/auth/services/auth.service';

export interface Product {
  id: number;
  name: string;
  sku: string;
  sale_price: number;
  stock: number;
  image_url?: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
  subtotal: number;
}

@Component({
  selector: 'app-sales',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterLink,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatSnackBarModule,
  ],
  templateUrl: './sales.component.html',
  styleUrl: './sales.component.scss',
})
export class SalesComponent implements OnInit {
  // Estado
  isLoadingProducts = false;
  isProcessingPayment = false;
  isMobileMenuOpen = false;

  // Datos
  products: Product[] = [];
  filteredProducts: Product[] = [];
  cart: CartItem[] = [];
  cartTotal = 0;
  searchQuery = '';

  // Datos del Cliente y Pago
  clientName = '';
  clientDocument = '';
  paymentMethod = 'Efectivo';

  private authService = inject(AuthService);
  private snackBar = inject(MatSnackBar);

  ngOnInit(): void {
    this.loadProducts();
  }

  // ── LÓGICA DE LA INTERFAZ ──
  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
  }
  // ── CATÁLOGO DE PRODUCTOS (DESDE LA BASE DE DATOS) ──
  loadProducts(): void {
    this.isLoadingProducts = true;
    this.authService.getProducts().subscribe({
      next: (data: any[]) => {
        this.products = data.filter((p) => p.is_active);
        this.filteredProducts = [...this.products];
        this.isLoadingProducts = false;
      },
      error: () => {
        this.isLoadingProducts = false;
        this.showMessage('Error al cargar el catálogo');
      },
    });
  }

  filterProducts(event: Event): void {
    const query = (event.target as HTMLInputElement).value.toLowerCase();
    this.searchQuery = query;
    this.filteredProducts = this.products.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.sku.toLowerCase().includes(query),
    );
  }

  // ── LÓGICA DEL CARRITO ──
  addToCart(product: Product): void {
    if (product.stock <= 0) {
      this.showMessage('Producto sin stock disponible');
      return;
    }

    const existingItem = this.cart.find(
      (item) => item.product.id === product.id,
    );

    if (existingItem) {
      if (existingItem.quantity >= product.stock) {
        this.showMessage('Límite de stock alcanzado');
        return;
      }
      existingItem.quantity++;
      existingItem.subtotal = existingItem.quantity * product.sale_price;
    } else {
      this.cart.push({ product, quantity: 1, subtotal: product.sale_price });
    }
    this.calculateTotal();
  }

  increaseQuantity(item: CartItem): void {
    if (item.quantity >= item.product.stock) {
      this.showMessage('Límite de stock alcanzado');
      return;
    }
    item.quantity++;
    item.subtotal = item.quantity * item.product.sale_price;
    this.calculateTotal();
  }

  decreaseQuantity(item: CartItem): void {
    if (item.quantity > 1) {
      item.quantity--;
      item.subtotal = item.quantity * item.product.sale_price;
    } else {
      this.removeFromCart(item);
    }
    this.calculateTotal();
  }

  removeFromCart(item: CartItem): void {
    this.cart = this.cart.filter(
      (cartItem) => cartItem.product.id !== item.product.id,
    );
    this.calculateTotal();
  }

  clearCart(): void {
    this.cart = [];
    this.clientName = '';
    this.clientDocument = '';
    this.paymentMethod = 'Efectivo';
    this.calculateTotal();
  }

  calculateTotal(): void {
    this.cartTotal = this.cart.reduce((acc, item) => acc + item.subtotal, 0);
  }

  // ── PROCESAR COBRO ──
  checkout(): void {
    if (this.cart.length === 0) return;
    this.isProcessingPayment = true;

    const saleData = {
      client_name: this.clientName || 'Cliente de Mostrador',
      client_document: this.clientDocument,
      payment_method: this.paymentMethod,
      details: this.cart.map((item) => ({
        product_id: item.product.id,
        quantity: item.quantity,
        unit_price: item.product.sale_price,
      })),
    };

    this.authService.createPosSale(saleData).subscribe({
      next: () => {
        this.isProcessingPayment = false;
        this.showMessage('¡Venta procesada con éxito!');
        this.clearCart();
        this.loadProducts(); // Recarga los productos para actualizar el stock real en pantalla
      },
      error: (err) => {
        this.isProcessingPayment = false;
        this.showMessage(err.error?.detail || 'Error al procesar la venta');
      },
    });
  }

  private showMessage(msg: string): void {
    this.snackBar.open(msg, 'Cerrar', {
      duration: 3000,
      horizontalPosition: 'right',
      verticalPosition: 'bottom',
    });
  }

  logout(): void {
    this.authService.logout();
  }
}
