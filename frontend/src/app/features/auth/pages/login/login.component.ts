import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'; // <- El loader
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatCheckboxModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
  // Esta animación hace que el contenido entre suavemente hacia arriba
  animations: [
    trigger('fadeInUp', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px)' }),
        animate('0.6s cubic-bezier(0.16, 1, 0.3, 1)', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ])
  ]
})
export class LoginComponent {
  loginForm: FormGroup;
  hidePassword = true;
  logoError = false;
  
  // Variable para controlar el estado de carga (Loader)
  isLoading = false;

  constructor(private fb: FormBuilder) {
    // Inicialización del formulario con sus validaciones
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      rememberMe: [false] // Captura el estado de "Mantenerme conectado"
    });
  }

  // Si la imagen del logo falla, muestra el texto por defecto
  handleLogoError() {
    this.logoError = true;
  }

  // Función que se ejecuta al presionar "Ingresar"
  onSubmit() {
    if (this.loginForm.valid) {
      // 1. Activamos el loader y deshabilitamos el botón
      this.isLoading = true;
      
      // 2. Extraemos los datos listos para enviar a FastAPI
      const loginData = this.loginForm.value;
      console.log('Datos listos para enviar al Backend:', loginData);
      // Fíjate en la consola del navegador: verás "rememberMe: true" o "false"

      // 3. Simulamos la petición al servidor (2 segundos de espera)
      // Cuando tengamos FastAPI, esto se reemplazará por un this.http.post(...)
      setTimeout(() => {
        this.isLoading = false;
        
        // Aquí iría la lógica de éxito:
        // localStorage.setItem('token', respuesta.token);
        // this.router.navigate(['/dashboard']);
        
      }, 2000);

    } else {
      // Si el usuario intentó enviar el formulario vacío, marcamos los errores en rojo
      this.loginForm.markAllAsTouched();
    }
  }
}