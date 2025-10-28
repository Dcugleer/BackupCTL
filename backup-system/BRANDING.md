# 🎨 Branding e Logo Customizada - BackupCTL

## Visão Geral

O BackupCTL agora suporta **logos customizadas** para personalização da marca! Esta funcionalidade permite que empresas e usuários personalizem a aparência do sistema com sua própria identidade visual.

## ✨ Funcionalidades

### 🖼️ **Upload de Logo**
- **Formatos suportados**: PNG, JPG, SVG, WebP
- **Tamanho recomendado**: 200x200px (quadrado)
- **Tamanho máximo**: 5MB
- **Fundo transparente** recomendado

### 🔄 **Preview em Tempo Real**
- Visualização instantânea da logo
- Preview de como aparecerá no header
- Redimensionamento automático

### 🎯 **Integração Perfeita**
- Substituição automática do ícone padrão
- Manutenção do layout responsivo
- Preservação da experiência do usuário

## 🚀 Como Usar

### 1. **Acessar a Aba Branding**
1. Abra a aplicação web: http://localhost:3000
2. Clique na aba **"Branding"**
3. Localize a seção **"Logo Customizada"**

### 2. **Fazer Upload da Logo**
1. Clique na área de upload ou arraste a imagem
2. Selecione seu arquivo de logo
3. Aguarde o processamento automático

### 3. **Visualizar e Ajustar**
1. Veja o preview em tempo real
2. Verifique como fica no layout
3. Se necessário, faça upload de outra imagem

### 4. **Remover Logo (Opcional)**
1. Clique no botão **"Remover Logo"**
2. O sistema voltará ao ícone padrão

## 📋 Diretrizes de Marca

### ✅ **Recomendações**
- **Qualidade**: Use imagens de alta resolução
- **Formato**: Logos quadradas funcionam melhor
- **Fundo**: Transparente para melhor integração
- **Cores**: Contraste bom com fundo claro
- **Simplicidade**: Designs limpos e reconhecíveis

### ❌ **Evitar**
- Imagens muito complexas ou detalhadas
- Logos retangulares (podem ser cortadas)
- Cores que se misturam com o fundo
- Texto muito pequeno ilegível
- Imagens de baixa qualidade

## 🔧 Configuração Avançada

### **Especificações Técnicas**
```yaml
# Configurações de logo
branding:
  logo:
    max_size: 5MB
    formats: ["png", "jpg", "svg", "webp"]
    recommended_size: "200x200px"
    aspect_ratio: "1:1 (square)"
    background: "transparent recommended"
```

### **CSS Classes Customizadas**
```css
/* Classes para customização */
.backupctl-logo {
  width: 80px;
  height: 80px;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.backupctl-logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

## 🎨 Exemplos de Uso

### **Corporativo**
```bash
# Logo da empresa no header
- Logo principal da empresa
- Cores institucionais mantidas
- Identidade visual preservada
```

### **Produto White-Label**
```bash
# Personalização para clientes
- Logo do cliente
- Cores do cliente
- Branding consistente
```

### **Projetos Pessoais**
```bash
# Identidade pessoal
- Logo pessoal
- Projeto específico
- Customização única
```

## 🔄 Fluxo de Trabalho

### **Upload → Preview → Aplicação**
```
1. Upload da imagem
2. Validação automática
3. Preview em tempo real
4. Aplicação no header
5. Salvamento automático
```

### **Fallback Automático**
```
Se a logo não carregar:
→ Exibe ícone padrão
→ Mantém funcionamento
→ Log de erro registrado
```

## 🛠️ Implementação Técnica

### **Frontend (React/Next.js)**
```typescript
// Componente de logo
const LogoDisplay = ({ customLogo }: { customLogo: string | null }) => {
  return customLogo ? (
    <img src={customLogo} alt="Custom Logo" className="backupctl-logo" />
  ) : (
    <DefaultLogoIcon />
  );
};
```

### **Upload Handler**
```typescript
// Processamento de upload
const handleLogoUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0];
  if (file) {
    const reader = new FileReader();
    reader.onloadend = () => {
      setCustomLogo(reader.result as string);
    };
    reader.readAsDataURL(file);
  }
};
```

### **Validação**
```typescript
// Validação de arquivo
const validateLogoFile = (file: File): boolean => {
  const validTypes = ['image/png', 'image/jpeg', 'image/svg+xml'];
  const maxSize = 5 * 1024 * 1024; // 5MB
  
  return validTypes.includes(file.type) && file.size <= maxSize;
};
```

## 📱 Responsividade

### **Mobile**
- Logo: 64x64px
- Layout adaptado
- Touch-friendly

### **Tablet**
- Logo: 80x80px
- Layout otimizado
- Good touch targets

### **Desktop**
- Logo: 80x80px
- Layout completo
- Hover effects

## 🔐 Segurança

### **Validação de Arquivos**
- Verificação de tipo MIME
- Limitação de tamanho
- Scan de conteúdo malicioso
- Sanitização de nomes

### **Storage**
- Base64 encoding no frontend
- Validação no backend
- Backup automático
- Versionamento

## 🚀 Futuras Melhorias

### **Planejado**
- [ ] Templates de logo pré-definidos
- [ ] Editor de logo integrado
- [ ] Suporte a animações
- [ ] Multiple logo variants
- [ ] Brand color customization

### **Roadmap**
- **v1.1**: Logo templates
- **v1.2**: Color customization
- **v1.3**: Advanced editor
- **v2.0**: Full branding suite

## 🆘 Troubleshooting

### **Problemas Comuns**

#### **Logo não aparece**
```bash
# Verifique:
- Formato do arquivo (PNG/JPG/SVG)
- Tamanho (< 5MB)
- Conexão com servidor
- Console errors
```

#### **Logo distorcida**
```bash
# Soluções:
- Use imagem quadrada
- Verifique resolução
- Teste outro formato
- Limpe cache do browser
```

#### **Upload falha**
```bash
# Verifique:
- Permissões do arquivo
- Espaço em disco
- Conexão internet
- Limites do servidor
```

### **Debug Mode**
```bash
# Ativar debug
localStorage.setItem('backupctl-debug', 'true');

# Verificar console
console.log('Logo state:', customLogo);
console.log('File validation:', validateLogoFile(file));
```

## 📞 Suporte

### **Documentação Relacionada**
- [README.md](./README.md) - Documentação principal
- [OVERVIEW.md](./OVERVIEW.md) - Visão geral do sistema
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Detalhes técnicos

### **Contato**
- Issues: GitHub Repository
- Email: backup-support@yourcompany.com
- Docs: Documentação completa

---

## 🎉 Conclusão

A funcionalidade de **logo customizada** torna o BackupCTL verdadeiramente **white-label** e adaptável para qualquer contexto corporativo ou pessoal!

**Personalize seu sistema de backup com sua própria marca!** 🚀

---

*BackupCTL - Backup automatizado com sua identidade visual* 🎨