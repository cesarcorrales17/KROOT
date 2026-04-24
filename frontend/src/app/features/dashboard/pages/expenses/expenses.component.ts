import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
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
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';

// SERVICIO
import { AuthService } from '../../../../features/auth/services/auth.service';

export interface ExpenseSummaryData {
  total_period_amount: number;
  categories_breakdown: any[];
}

@Component({
  selector: 'app-expenses',
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
    MatDatepickerModule,
    MatNativeDateModule,
  ],
  templateUrl: './expenses.component.html',
  styleUrl: './expenses.component.scss',
})
export class ExpensesComponent implements OnInit {
  expenseForm: FormGroup;
  isSaving = false;
  successMessage = '';
  errorMessage = '';

  currentCurrency = 'COP';
  todayExpensesCount = 0;

  // Variables para la HU Dual y Comparativas
  purchasesActive = false; // Simula la integración con Órdenes de Compra
  summary: ExpenseSummaryData | null = null;
  categories: any[] = []; // Se llenará desde la base de datos

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);

  constructor() {
    this.expenseForm = this.fb.group({
      amount: [null, [Validators.required, Validators.min(1)]],
      category_id: [null, Validators.required],
      period_type: ['monthly', Validators.required],
      period_date: [new Date(), Validators.required],
      supplier_name: [''],
      description: [''],
      receipt_ref: [''],
    });
  }

  // ── Estado del Menú Lateral ──────────────────────────────────────────────
  menuExpanded = {
    principal: true,
    finanzas: true,
    sistema: true,
  };

  toggleMenu(section: 'principal' | 'finanzas' | 'sistema'): void {
    this.menuExpanded[section] = !this.menuExpanded[section];
  }

  ngOnInit(): void {
    this.loadCategories();
    this.loadSummary('monthly');
  }

  // ── Estado del Menú Lateral (Móvil) ─────────────────────────────────────
  isMobileMenuOpen = false;

  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
  }

  // ── Simulador de la HU (Automático vs Manual) ──────────────────────────
  togglePurchaseIntegration(): void {
    this.purchasesActive = !this.purchasesActive;
  }

  // ── Carga de datos desde FastAPI ───────────────────────────────────────
  loadCategories(): void {
    // Estas son las categorías "quemadas" en el front que hacen match con la DB
    const defaultCategories = [
      { id: 1, name: 'Arriendo' },
      { id: 2, name: 'Nómina' },
      { id: 3, name: 'Servicios Públicos' },
      { id: 4, name: 'Marketing / Publicidad' },
      { id: 5, name: 'Insumos' },
      { id: 6, name: 'Otros' },
    ];

    this.authService.getExpenseCategories().subscribe({
      next: (data) => {
        // Si el backend trae datos, los usamos. Si viene vacío, usamos el fallback.
        if (data && data.length > 0) {
          this.categories = data;
        } else {
          console.warn(
            'Backend no trajo categorías. Usando fallback del frontend.',
          );
          this.categories = defaultCategories;
        }
      },
      error: (err) => {
        console.error(
          'Error de conexión. Usando categorías del frontend.',
          err,
        );
        this.categories = defaultCategories;
      },
    });
  }

  loadSummary(period: string): void {
    this.authService.getExpensesSummary(period).subscribe({
      next: (data) => (this.summary = data),
      error: (err) => console.error('Error cargando el resumen', err),
    });
  }

  // ── Helpers para la UI ──────────────────────────────────────────────────
  getCategoryName(): string {
    const id = this.expenseForm.get('category_id')?.value;
    if (!id) return 'Sin categoría';
    const cat = this.categories.find((c) => c.id === id);
    return cat ? cat.name : 'Desconocida';
  }

  logout(): void {
    this.authService.logout();
  }

  // ── Gestión de Categorías Personalizadas ────────────────────────────────
  isCreatingCategory = false;
  isSavingCategory = false;

  toggleCategoryMode(event?: Event): void {
    if (event) {
      event.preventDefault(); // Evita que el formulario haga submit por accidente
      event.stopPropagation();
    }
    this.isCreatingCategory = !this.isCreatingCategory;
  }

  saveNewCategory(catName: string): void {
    if (!catName || !catName.trim()) return;

    this.isSavingCategory = true;
    const categoryData = { name: catName.trim(), is_default: false };

    this.authService.createExpenseCategory(categoryData).subscribe({
      next: (newCat) => {
        // 1. Agregamos la nueva categoría al arreglo visual
        this.categories.push(newCat);

        // 2. Seleccionamos automáticamente la nueva categoría en el formulario
        this.expenseForm.patchValue({ category_id: newCat.id });

        // 3. Apagamos el spinner y volvemos a la vista del selector
        this.isSavingCategory = false;
        this.toggleCategoryMode();
      },
      error: (err) => {
        console.error('Error al crear la categoría', err);
        this.isSavingCategory = false;
        this.errorMessage = 'Hubo un error al guardar la categoría.';
        setTimeout(() => (this.errorMessage = ''), 4000);
      },
    });
  }

  // ── Guardar Gasto ───────────────────────────────────────────────────────
  onSubmit(): void {
    if (this.expenseForm.invalid) {
      this.expenseForm.markAllAsTouched();
      return;
    }

    this.isSaving = true;
    this.successMessage = '';
    this.errorMessage = '';

    const formValue = { ...this.expenseForm.value };

    // Formatea la fecha a YYYY-MM-DD para FastAPI
    if (formValue.period_date) {
      const d = new Date(formValue.period_date);
      formValue.period_date = d.toISOString().split('T')[0];
    }

    this.authService.createManualExpense(formValue).subscribe({
      next: () => {
        this.isSaving = false;
        this.successMessage = 'Gasto registrado correctamente.';
        this.todayExpensesCount++;

        // Recarga el resumen para actualizar el widget al instante
        this.loadSummary(
          this.expenseForm.get('period_type')?.value || 'monthly',
        );

        // Limpia los campos variables
        this.expenseForm.patchValue({
          amount: null,
          supplier_name: '',
          description: '',
          receipt_ref: '',
        });

        setTimeout(() => (this.successMessage = ''), 4000);
      },
      error: (err) => {
        this.isSaving = false;
        this.errorMessage = err.error?.detail || 'Error al registrar el gasto.';
      },
    });
  }
}
