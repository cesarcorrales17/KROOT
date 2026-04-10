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

@Component({
  selector: 'app-sales',
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
  templateUrl: './sales.component.html',
  styleUrl: './sales.component.scss',
})
export class SalesComponent implements OnInit {
  salesForm: FormGroup;
  isSaving = false;
  successMessage = '';
  errorMessage = '';

  summary: any = null;
  isLoadingSummary = true;
  currentCurrency = 'COP';

  // Nuevas opciones para hacer el formulario robusto
  categories = [
    'Producto Físico',
    'Servicio',
    'Reparación',
    'Suscripción',
    'Otro',
  ];
  paymentMethods = ['Efectivo', 'Transferencia', 'Tarjeta', 'Otro'];

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);

  constructor() {
    this.salesForm = this.fb.group({
      amount: ['', [Validators.required, Validators.min(1)]],
      period_type: ['monthly', Validators.required],
      period_date: [new Date(), Validators.required], // Inicia con fecha actual
      category: [''],
      payment_method: [''],
      description: [''],
    });
  }

  ngOnInit(): void {
    this.loadSummary('monthly');
  }

  loadSummary(periodType: string): void {
    this.isLoadingSummary = true;
    this.authService.getSalesSummary(periodType).subscribe({
      next: (data) => {
        this.summary = data;
        this.isLoadingSummary = false;
      },
      error: (err) => {
        console.error('Error cargando resumen', err);
        this.isLoadingSummary = false;
      },
    });
  }

  onPeriodChange(event: any): void {
    this.loadSummary(event.value);
  }

  onSubmit(): void {
    if (this.salesForm.invalid) {
      this.salesForm.markAllAsTouched();
      return;
    }

    this.isSaving = true;
    this.successMessage = '';
    this.errorMessage = '';

    // Clonamos los datos para formatear la fecha correctamente para FastAPI (YYYY-MM-DD)
    const formValue = { ...this.salesForm.value };
    if (formValue.period_date) {
      const d = new Date(formValue.period_date);
      formValue.period_date = d.toISOString().split('T')[0];
    }

    this.authService.createSale(formValue).subscribe({
      next: (response) => {
        this.isSaving = false;
        this.successMessage = 'Venta registrada correctamente.';

        this.loadSummary(this.salesForm.get('period_type')?.value);

        // Limpiamos solo los campos variables, dejamos la fecha y tipo iguales
        this.salesForm.patchValue({
          amount: '',
          description: '',
        });

        setTimeout(() => (this.successMessage = ''), 4000);
      },
      error: (err) => {
        this.isSaving = false;
        this.errorMessage = err.error?.detail || 'Error al registrar la venta.';
      },
    });
  }

  logout(): void {
    this.authService.logout();
  }
}
