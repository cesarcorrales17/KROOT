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

  currentCurrency = 'COP';
  todaySalesCount = 0;

  // ── Opciones de selección ────────────────────────────────────────────────
  categories = [
    'Producto Físico',
    'Servicio',
    'Reparación',
    'Suscripción',
    'Otro',
  ];

  paymentMethods = ['Efectivo', 'Transferencia', 'Tarjeta', 'Otro'];

  clientTypes = [
    'Persona Natural',
    'Empresa',
    'Cliente Recurrente',
    'Cliente Nuevo',
    'Otro',
  ];

  paymentStatuses = [
    { value: 'paid', label: 'Pagado' },
    { value: 'pending', label: 'Pendiente' },
    { value: 'partial', label: 'Pago Parcial' },
    { value: 'cancelled', label: 'Cancelado' },
  ];

  private fb = inject(FormBuilder);
  private authService = inject(AuthService);

  constructor() {
    // Hora actual en formato HH:MM para el campo sale_time
    const now = new Date();
    const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    this.salesForm = this.fb.group({
      // Datos del cliente
      client_name: [''],
      client_type: [''],
      client_contact: [''],
      client_document: [''],

      // Detalle del producto/servicio
      category: [''],
      product_name: [''],
      quantity: [1, [Validators.required, Validators.min(1)]],
      unit_price: [0, [Validators.required, Validators.min(0)]],
      description: [''],

      // Información financiera
      amount: [
        { value: 0, disabled: false },
        [Validators.required, Validators.min(1)],
      ],
      payment_method: [''],
      payment_status: ['paid'],
      period_type: ['monthly', Validators.required],

      // Datos de control
      period_date: [new Date(), Validators.required],
      sale_time: [hhmm],
      invoice_ref: [''],
    });
  }

  ngOnInit(): void {
    this.loadTodaySalesCount();
  }

  // ── Cálculo automático del monto ─────────────────────────────────────────
  recalculateAmount(): void {
    const qty = parseFloat(this.salesForm.get('quantity')?.value) || 0;
    const price = parseFloat(this.salesForm.get('unit_price')?.value) || 0;
    this.salesForm.patchValue({ amount: qty * price }, { emitEvent: false });
  }

  // ── Helpers para el panel de resumen ─────────────────────────────────────
  getClientInitials(): string {
    const name: string = this.salesForm.get('client_name')?.value || '';
    return name
      .split(' ')
      .slice(0, 2)
      .map((w: string) => w.charAt(0).toUpperCase())
      .join('');
  }

  getPaymentStatusLabel(): string {
    const val = this.salesForm.get('payment_status')?.value;
    return this.paymentStatuses.find((s) => s.value === val)?.label ?? '';
  }

  getPaymentStatusClass(): string {
    const map: Record<string, string> = {
      paid: 'status-paid',
      pending: 'status-pending',
      partial: 'status-partial',
      cancelled: 'status-cancelled',
    };
    return map[this.salesForm.get('payment_status')?.value] ?? 'status-default';
  }

  getPaymentStatusIcon(): string {
    const map: Record<string, string> = {
      paid: 'check_circle',
      pending: 'schedule',
      partial: 'timelapse',
      cancelled: 'cancel',
    };
    return map[this.salesForm.get('payment_status')?.value] ?? 'info';
  }

  // ── Carga de ventas de hoy (conectar cuando exista el endpoint) ───────────
  loadTodaySalesCount(): void {
    this.todaySalesCount = 0;
  }

  // ── Envío del formulario ──────────────────────────────────────────────────
  onSubmit(): void {
    if (this.salesForm.invalid) {
      this.salesForm.markAllAsTouched();
      return;
    }

    this.isSaving = true;
    this.successMessage = '';
    this.errorMessage = '';

    const formValue = { ...this.salesForm.value };

    // Formatea la fecha a YYYY-MM-DD para FastAPI
    if (formValue.period_date) {
      const d = new Date(formValue.period_date);
      formValue.period_date = d.toISOString().split('T')[0];
    }

    this.authService.createSale(formValue).subscribe({
      next: () => {
        this.isSaving = false;
        this.successMessage = 'Venta registrada correctamente.';
        this.todaySalesCount++;

        // Limpia solo los campos variables; conserva fecha, hora y período
        const now = new Date();
        const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

        this.salesForm.patchValue({
          client_name: '',
          client_contact: '',
          client_document: '',
          product_name: '',
          quantity: 1,
          unit_price: 0,
          amount: 0,
          invoice_ref: '',
          description: '',
          sale_time: hhmm,
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
