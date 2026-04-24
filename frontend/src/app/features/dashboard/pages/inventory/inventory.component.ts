import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';

// MATERIAL DESIGN
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

// SERVICIO
import { AuthService } from '../../../../features/auth/services/auth.service';

export interface ProductData {
  id: number;
  name: string;
  sku: string;
  barcode?: string;
  sale_price: number;
  cost_price: number;
  unit: string;
  is_active: boolean;
  min_stock: number;
  stock: number;
  category_id?: number;
  image_url?: string;
}

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  templateUrl: './inventory.component.html',
  styleUrl: './inventory.component.scss',
})
export class InventoryComponent implements OnInit {
  // Estado de la UI
  isLoading = false;
  isSaving = false;
  isDrawerOpen = false;
  editingProductId: number | null = null;
  imagePreview: string | null = null; // Corregido: imagePreview

  // Control de vista
  viewMode: 'list' | 'card' = 'card'; // Por defecto iniciará en tarjetas

  toggleViewMode(mode: 'list' | 'card'): void {
    this.viewMode = mode;
  }

  // Mensajes
  successMessage = '';
  errorMessage = '';

  // Datos
  products: ProductData[] = [];
  categories: any[] = [];
  productForm: FormGroup;

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);

  constructor() {
    this.productForm = this.fb.group({
      name: ['', Validators.required],
      category_id: [null],
      sku: ['', Validators.required],
      barcode: [''],
      sale_price: [null, [Validators.required, Validators.min(0)]],
      cost_price: [null, [Validators.min(0)]],
      min_stock: [5, [Validators.required, Validators.min(0)]],
      stock: [0, [Validators.required, Validators.min(0)]],
      unit: ['unidad', Validators.required],
      description: [''],
      image_url: [null],
    });
  }

  ngOnInit(): void {
    this.loadProducts();
    this.loadCategories();
  }

  isMobileMenuOpen = false;

  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
  }

  // Carga de datos
  loadProducts(): void {
    this.isLoading = true;
    this.authService.getProducts().subscribe({
      next: (data) => {
        this.products = data;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error al cargar productos', err);
        this.isLoading = false;
      },
    });
  }

  loadCategories(): void {
    // Fallback genérico para cualquier negocio
    const defaultCategories = [
      { id: 1, name: 'General' },
      { id: 2, name: 'Servicios' },
      { id: 3, name: 'Productos Físicos' },
      { id: 4, name: 'Insumos' },
    ];

    this.categories = defaultCategories;
  }

  // Control del Panel Lateral (Drawer)
  openDrawer(product?: ProductData): void {
    this.successMessage = '';
    this.errorMessage = '';
    this.imagePreview = null; // Resetea la imagen al abrir

    if (product) {
      this.editingProductId = product.id;
      this.productForm.patchValue(product);
      // Si el producto tiene imagen, la mostramos en la vista previa
      if (product.image_url) {
        this.imagePreview = product.image_url;
      }
    } else {
      this.editingProductId = null;
      this.productForm.reset({ unit: 'unidad', min_stock: 5 });
    }
    this.isDrawerOpen = true;
  }

  closeDrawer(): void {
    this.isDrawerOpen = false;
    this.editingProductId = null;
    this.imagePreview = null;
  }

  // Procesamiento de Imagen
  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      // Validar que sea un archivo de imagen
      if (!file.type.startsWith('image/')) {
        this.errorMessage = 'Solo se permiten archivos de imagen.';
        setTimeout(() => (this.errorMessage = ''), 4000);
        return;
      }

      // Convertir a Base64 para guardarlo en la base de datos
      const reader = new FileReader();
      reader.onload = () => {
        this.imagePreview = reader.result as string;
        this.productForm.patchValue({ image_url: this.imagePreview });
      };
      reader.readAsDataURL(file);
    }
  }

  // Acciones CRUD
  onSubmit(): void {
    if (this.productForm.invalid) {
      this.productForm.markAllAsTouched();
      return;
    }

    this.isSaving = true;
    this.errorMessage = '';

    const formData = this.productForm.value;

    if (this.editingProductId) {
      // Editar
      this.authService
        .updateProduct(this.editingProductId, formData)
        .subscribe({
          next: () => {
            this.isSaving = false;
            this.successMessage = 'Producto actualizado correctamente.';
            this.loadProducts();
            this.closeDrawer();
            this.clearMessageAfterDelay();
          },
          error: (err) => this.handleError(err),
        });
    } else {
      // Crear
      this.authService.createProduct(formData).subscribe({
        next: () => {
          this.isSaving = false;
          this.successMessage = 'Producto creado correctamente.';
          this.loadProducts();
          this.closeDrawer();
          this.clearMessageAfterDelay();
        },
        error: (err) => this.handleError(err),
      });
    }
  }

  deleteProduct(): void {
    if (!this.editingProductId) return;

    if (
      confirm(
        '¿Estás seguro de que deseas eliminar este producto? Esta acción no se puede deshacer.',
      )
    ) {
      this.isSaving = true;
      this.authService.deleteProduct(this.editingProductId).subscribe({
        next: () => {
          this.isSaving = false;
          this.successMessage = 'Producto eliminado correctamente.';
          this.loadProducts();
          this.closeDrawer();
          this.clearMessageAfterDelay();
        },
        error: (err) => this.handleError(err),
      });
    }
  }

  toggleStatus(productId: number): void {
    this.authService.toggleProductStatus(productId).subscribe({
      next: () => {
        this.successMessage = 'Estado actualizado.';
        this.loadProducts();
        this.clearMessageAfterDelay();
      },
      error: (err) => this.handleError(err),
    });
  }

  // Helpers
  getCategoryName(id: number | undefined): string {
    if (!id) return 'Sin categoría';
    const cat = this.categories.find((c) => c.id === id);
    return cat ? cat.name : 'Desconocida';
  }

  private handleError(err: any): void {
    this.isSaving = false;
    this.errorMessage =
      err.error?.detail || 'Ha ocurrido un error en la operación.';
    this.clearMessageAfterDelay();
  }

  private clearMessageAfterDelay(): void {
    setTimeout(() => {
      this.successMessage = '';
      this.errorMessage = '';
    }, 4000);
  }

  logout(): void {
    this.authService.logout();
  }
}
